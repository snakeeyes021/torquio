"""Run Torquio flows in two copies of the repo (before and after a change) and compare what the user sees.

Each run gets:
- its own copy of the repo (a shared git clone; the "new" side has the working tree's uncommitted and
  untracked changes committed on top, so both are clean checkouts with no upstream branch),
- the same scratch $HOME (emptied between runs, so paths in the output are identical) with no XDG_* set,
- a pseudo-terminal with echo turned off (prompts appear as on a real terminal; typed input doesn't, so
  the output doesn't depend on timing), TERM=xterm-256color, a fixed size, LANG=C.UTF-8 and TZ=UTC,
- fake versions of the programs that reach outside $HOME (sudo, distrobox, podman, gsettings, ...), no
  session bus or display, and no network (unshare), so nothing can touch the real system or container.

Compared: the terminal output (with times, dates and the scratch paths masked), the exit code, the files
left in $HOME (names, with timestamps masked, and the members of zips) and the contents of the files a scenario lists.
"""
import difflib
import os
import re
import select
import shutil
import signal
import struct
import subprocess
import tempfile
import termios
import fcntl
import time
import zipfile

FAKES = {
    # program: shell body (prints nothing and fails unless given here)
    "distrobox": 'case "$1" in list) exit 0 ;; esac; exit 1',
    "xdg-user-dir": 'echo "$HOME/Downloads"',
}
FAKE_FAILING = ["sudo", "pkexec", "podman", "docker", "gsettings", "dconf", "kwriteconfig5", "kwriteconfig6",
                "kreadconfig5", "kreadconfig6", "kscreen-doctor", "cosmic-randr", "xrandr", "modprobe",
                "systemctl", "flatpak", "notify-send", "xdg-open", "pkill", "killall"]

MASKS = [
    (re.compile(r"\b\w{3} \w{3} [ \d]\d \d\d:\d\d:\d\d [A-Z]+ \d{4}\b"), "<DATE>"),  # date
    (re.compile(r"\d{4}-\d\d-\d\d[_ ]\d\d[-:]\d\d[-:]\d\d"), "<STAMP>"),
]


def git(*args, cwd=None, **kwargs):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, **kwargs).stdout


def make_copy(repo, ref, dest, with_working_tree=False):
    """A clean clone of `repo` at `ref` in `dest`; optionally with the working tree's changes committed."""
    commit = git("rev-parse", "--verify", ref + "^{commit}", cwd=repo).strip()
    git("clone", "-q", "--shared", "--no-checkout", repo, dest)
    git("checkout", "-q", "--detach", commit, cwd=dest)
    if with_working_tree:
        diff = subprocess.run(["git", "diff", "HEAD", "--binary"], cwd=repo, check=True, capture_output=True).stdout
        if diff:
            subprocess.run(["git", "apply", "--whitespace=nowarn"], cwd=dest, input=diff, check=True)
        for rel in git("ls-files", "--others", "--exclude-standard", "-z", cwd=repo).split("\0"):
            if rel:
                os.makedirs(os.path.dirname(os.path.join(dest, rel)), exist_ok=True)
                shutil.copy2(os.path.join(repo, rel), os.path.join(dest, rel))
        git("add", "-A", cwd=dest)
        if git("status", "--porcelain", cwd=dest):
            git("-c", "user.name=parity", "-c", "user.email=parity@localhost", "commit", "-q", "-m",
                "working tree", cwd=dest)


def make_fakes(bindir):
    os.makedirs(bindir, exist_ok=True)
    bodies = dict(FAKES, **{name: "exit 1" for name in FAKE_FAILING if name not in FAKES})
    for name, body in bodies.items():
        path = os.path.join(bindir, name)
        with open(path, "w") as f:
            f.write(f"#!/bin/sh\n{body}\n")
        os.chmod(path, 0o755)


def environment(home, bindir):
    env = {
        "HOME": home, "USER": os.environ.get("USER", "user"), "LOGNAME": os.environ.get("LOGNAME", "user"),
        "PATH": bindir + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
        "TERM": "xterm-256color", "LANG": "C.UTF-8", "TZ": "UTC",
        "XDG_RUNTIME_DIR": os.path.join(home, ".run"),
        "XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "GNOME",
    }
    return env


def run_in_pty(cmd, env, cwd, stdin_text, timeout=120):
    """(output with \\r\\n turned into \\n, exit code); -9 if it had to be killed."""
    master, slave = os.openpty()
    attrs = termios.tcgetattr(slave)
    attrs[3] &= ~(termios.ECHO | termios.ECHONL)
    termios.tcsetattr(slave, termios.TCSANOW, attrs)
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))
    proc = subprocess.Popen(cmd, env=env, cwd=cwd, stdin=slave, stdout=slave, stderr=slave,
                            start_new_session=True)
    os.close(slave)
    if stdin_text:
        os.write(master, stdin_text.encode())
    out, deadline, killed = bytearray(), time.monotonic() + timeout, False
    while True:
        if time.monotonic() > deadline and not killed:
            os.killpg(proc.pid, signal.SIGKILL)
            killed = True
        ready, _, _ = select.select([master], [], [], 0.5)
        if ready:
            try:
                data = os.read(master, 65536)
            except OSError:  # EIO: every process holding the terminal has gone
                break
            if not data:
                break
            out += data
        elif proc.poll() is not None and killed:
            break
    os.close(master)
    code = proc.wait()
    return out.decode("utf-8", "replace").replace("\r\n", "\n"), (-9 if killed else code)


def mask(text, replacements):
    for old, new in replacements:
        text = text.replace(old, new)
    for pattern, new in MASKS:
        text = pattern.sub(new, text)
    return text


def snapshot(home, compare_files, replacements):
    """Masked names of the files in $HOME, and the contents of the listed ones."""
    names = []
    for root, dirs, files in os.walk(home):
        dirs.sort()
        for name in sorted(files):
            path = os.path.join(root, name)
            names.append(mask(os.path.relpath(path, home), replacements))
            if name.endswith(".zip"):  # e.g. the log export: compare what's inside too
                try:
                    with zipfile.ZipFile(path) as z:
                        names += [mask(f"{os.path.relpath(path, home)}!{m}", replacements) for m in z.namelist()]
                except zipfile.BadZipFile:
                    names.append(mask(f"{os.path.relpath(path, home)}!<not a zip>", replacements))
    contents = {}
    for rel in compare_files:
        path = os.path.join(home, rel)
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                contents[rel] = mask(f.read(), replacements)
        except OSError:
            contents[rel] = None
    return sorted(names), contents


def run_scenario(scenario, repo_copy, workdir):
    """Run one scenario in `repo_copy`; returns a dict of everything compared."""
    home = os.path.join(workdir, "home")
    shutil.rmtree(home, ignore_errors=True)
    os.makedirs(os.path.join(home, ".run"), mode=0o700)
    for rel, text in scenario.get("files", {}).items():
        path = os.path.join(home, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)
    bindir = os.path.join(workdir, "fakebin")
    env = environment(home, bindir)
    cmd = [os.path.join(repo_copy, "torquio"), *scenario.get("args", [])]
    if shutil.which("unshare"):
        cmd = ["unshare", "--map-current-user", "--net", "--", *cmd]
    output, code = run_in_pty(cmd, env, home, scenario.get("input", ""), scenario.get("timeout", 120))
    replacements = [(repo_copy, "<REPO>"), (home, "<HOME>"), (workdir, "<TMP>")]
    names, contents = snapshot(home, scenario.get("compare_files", []), replacements)
    return {"output": mask(output, replacements), "exit code": code, "files": names, "contents": contents}


def diff(a, b, label):
    """Unified diff lines between two results (empty if they match)."""
    lines = []
    for key in a:
        if a[key] == b[key]:
            continue
        if isinstance(a[key], str):
            left, right = a[key].splitlines(keepends=True), b[key].splitlines(keepends=True)
        elif isinstance(a[key], dict):
            left = [f"{k}:\n{v}\n" for k, v in sorted(a[key].items(), key=str)]
            right = [f"{k}:\n{v}\n" for k, v in sorted(b[key].items(), key=str)]
        elif isinstance(a[key], list):
            left, right = [f"{x}\n" for x in a[key]], [f"{x}\n" for x in b[key]]
        else:
            left, right = [f"{a[key]!r}\n"], [f"{b[key]!r}\n"]
        lines += difflib.unified_diff(left, right, f"{label} {key} (before)", f"{label} {key} (after)")
    return lines


class Copies:
    """The two repo copies and a scratch area, removed afterwards."""

    def __init__(self, repo, base_ref, keep=False):
        self.repo, self.base_ref, self.keep = repo, base_ref, keep

    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="torquio-parity-")
        self.base = os.path.join(self.tmp, "before", "torquio")
        self.new = os.path.join(self.tmp, "after", "torquio")
        make_copy(self.repo, self.base_ref, self.base)
        make_copy(self.repo, "HEAD", self.new, with_working_tree=True)
        make_fakes(os.path.join(self.tmp, "fakebin"))
        return self

    def __exit__(self, *exc):
        if self.keep:
            print(f"Kept {self.tmp}")
        else:
            shutil.rmtree(self.tmp, ignore_errors=True)
