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

# The fake container is driven by FAKE_* variables a scenario sets (scenarios.py describes them); without
# FAKE_CONTAINER there is none. The repo copy is found through TORQUIO_INSTALLERS_DIR (common.sh exports it).
FAKE_DISTROBOX = r"""
repo="${TORQUIO_INSTALLERS_DIR%/installers}"
# A container created during the scenario (distrobox create) exists until it's removed (distrobox rm)
[ -z "$FAKE_CONTAINER" ] && [ -f "$HOME/.fake-container" ] && FAKE_CONTAINER=$(cat "$HOME/.fake-container")
case "$1" in
list)
    [ -n "$FAKE_CONTAINER" ] || exit 0
    echo "ID           | NAME                 | STATUS             | IMAGE"
    echo "0123456789ab | $FAKE_CONTAINER          | ${FAKE_STATUS-Up 2 hours}         | x"
    exit 0 ;;
create)
    if [ "${FAKE_CREATE_RC:-0}" = 0 ]; then
        name=""; prev=""
        for arg in "$@"; do [ "$prev" = "-n" ] && name="$arg"; prev="$arg"; done
        [ "$name" = torquio-env ] && echo "$name" > "$HOME/.fake-container"
    fi
    exit "${FAKE_CREATE_RC:-0}" ;;
rm) [ "$2" = torquio-env ] && rm -f "$HOME/.fake-container"; exit 0 ;;
stop) exit 0 ;;
enter)
    [ -n "$FAKE_CONTAINER" ] || exit 1
    [ "$6" = "vulkaninfo --summary 2>/dev/null" ] && { printf '%b' "$FAKE_VULKANINFO"; exit 0; }
    case "$*" in
    *"sudo tee /var/lib/dbus/machine-id"*)
        printf '%s' "$6" | sed -n 's/.*echo \([0-9a-f]*\) | sudo tee.*/\1/p' > "$HOME/.fake-machine-id" ;;
    *"cat /var/lib/dbus/machine-id"*)
        if [ -f "$HOME/.fake-machine-id" ]; then
            cat "$HOME/.fake-machine-id"
        elif [ "$FAKE_MACHINE_ID" = derived ]; then
            printf 'torquio:%s' "$(cat /etc/machine-id)" | sha256sum | cut -c1-32
        else
            printf '%s\n' "$FAKE_MACHINE_ID"
        fi ;;
    *build-info*)
        if [ "$FAKE_BUILD_INFO" = matching ]; then
            echo "zhiyi_commit=$(sed -n 's/^TARGET_COMMIT="\(.*\)"$/\1/p' "$repo/scripts/1-build/build_wine.sh")"
            for p in "$repo"/scripts/1-build/patches/*.patch; do
                echo "patch=$(sha256sum "$p" | cut -c1-12) $(basename "$p" .patch)"
            done
            echo "torquio_commit=0123abc"
        else
            printf '%b' "$FAKE_BUILD_INFO"
        fi ;;
    *vulkaninfo*) printf '%b' "$FAKE_PROBE" ;;
    *"test -x"*) exit "${FAKE_NEW_WINE_RC:-0}" ;;
    *"wine reg query"*) printf '%b' "$FAKE_REG_QUERY" ;;
    *"ps auxww"*) printf '%b' "$FAKE_PS" ;;
    *run-dorico.sh|*run-sam.sh|*run-sda.sh) exit "${FAKE_RUNNER_RC:-0}" ;;
    *libGLX_nvidia*) [ "$FAKE_CONTAINER_NVIDIA" = yes ] ;;
    *"command -v xev"*) [ "$FAKE_XEV" = yes ] ;;
    *"build_wine.sh --rebuild"*) echo "(fake) building Wine"; exit "${FAKE_BUILD_RC:-0}" ;;
    *extract_icons.sh*|*setup_prefix.sh*|*container_gpu_setup.sh*) echo "(fake) ran ${6##*./}" ;;
    *) exit 0 ;;
    esac ;;
*) exit 1 ;;
esac
"""
FAKE_PODMAN = r"""
repo="${TORQUIO_INSTALLERS_DIR%/installers}"
case "$1 $2" in
"container inspect")
    [ -n "$FAKE_CONTAINER" ] || exit 125
    if [ "$FAKE_IMAGE" = current ]; then
        echo "ghcr.io/snakeeyes021/torquio-env:build-$(git -C "$repo" rev-parse HEAD:scripts/1-build | cut -c1-12)"
    else
        printf '%s\n' "$FAKE_IMAGE"
    fi ;;
"image inspect") [ "$FAKE_IMAGE_PRESENT" = yes ] ;;
"images "*) printf '%b' "$FAKE_IMAGES" ;;
"pull "*) echo "(fake) pulling $2"; exit "${FAKE_PULL_RC:-0}" ;;
"commit "*) exit "${FAKE_COMMIT_RC:-0}" ;;
"rename "*|"rmi "*) exit 0 ;;
*) exit 125 ;;
esac
"""

FAKES = {
    # program: shell body (prints nothing and fails unless given here)
    "distrobox": FAKE_DISTROBOX,
    "podman": FAKE_PODMAN,
    "xdg-user-dir": 'echo "$HOME/Downloads"',
    "gsettings": '[ "$1" = list-schemas ] && [ "$FAKE_MUTTER_WAYLAND" = yes ] && { echo org.gnome.mutter.wayland; exit 0; }; '
                 '[ "$1 $3" = "get xwayland-scaling-factor" ] && [ -n "$FAKE_XWAYLAND_FACTOR" ] && '
                 '{ printf "%s\\n" "$FAKE_XWAYLAND_FACTOR"; exit 0; }; [ "$1" = set ]',
    "kreadconfig6": 'printf "%s\\n" "$FAKE_KDE_POLICY"',
    "modinfo": '[ "$FAKE_NTSYNC_MODULE" = yes ]',
    "zenity": '[ -n "$FAKE_PICKED" ] && printf "%s\\n" "$FAKE_PICKED"',
    "kdialog": '[ -n "$FAKE_PICKED" ] && printf "%s\\n" "$FAKE_PICKED"',
    "nohup": "exit 0",  # the installer's background Download Assistant start: recorded, not run
}
FAKE_FAILING = ["sudo", "pkexec", "docker", "gsettings", "dconf", "kwriteconfig5", "kwriteconfig6",
                "kreadconfig5", "kscreen-doctor", "cosmic-randr", "xrandr", "modprobe",
                "systemctl", "flatpak", "notify-send", "xdg-open", "pkill", "killall", "dbus-send",
                # terminals (the Activation Manager launcher can open Torquio in one)
                "xdg-terminal-exec", "gnome-terminal", "ptyxis", "tilix", "konsole", "xfce4-terminal", "alacritty",
                "kitty", "xterm"]

MASKS = [
    (re.compile(r"\b\w{3} \w{3} [ \d]\d \d\d:\d\d:\d\d [A-Z]+ \d{4}\b"), "<DATE>"),  # date
    (re.compile(r"\d{4}-\d\d-\d\d[_ ]\d\d[-:]\d\d[-:]\d\d"), "<STAMP>"),
    (re.compile(r"\b20\d{12}\b"), "<STAMP>"),  # date +%Y%m%d%H%M%S (container snapshots)
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
    git("update-ref", "refs/parity/base", "HEAD", cwd=dest)  # what GIT_TEARDOWN returns to


# Every call to a fake except these read-only ones is recorded in ~/.fake-calls, which is compared too: the
# same commands must reach the container and the desktop settings.
LOG_CALL = r"""case "$(basename "$0") $1" in
"distrobox list"|"podman container"|"gsettings get"|"gsettings list-schemas"|kreadconfig*|"modinfo "*|"xdg-user-dir "*) ;;
*) printf '%s\n' "$(basename "$0") $*" >> "$HOME/.fake-calls" ;;
esac
"""


def make_fakes(bindir, bodies=None, defaults=True):
    os.makedirs(bindir, exist_ok=True)
    if defaults:
        bodies = dict(FAKES, **{name: "exit 1" for name in FAKE_FAILING if name not in FAKES})
    for name, body in (bodies or {}).items():
        path = os.path.join(bindir, name)
        with open(path, "w") as f:
            f.write(f"#!/bin/sh\n{LOG_CALL}{body}\n")
        os.chmod(path, 0o755)


def environment(home, bindir, extra=None):
    env = {
        "HOME": home, "USER": os.environ.get("USER", "user"), "LOGNAME": os.environ.get("LOGNAME", "user"),
        "PATH": bindir + ":" + os.environ.get("PATH", "/usr/bin:/bin"),
        "TERM": "xterm-256color", "LANG": "C.UTF-8", "TZ": "UTC",
        "XDG_RUNTIME_DIR": os.path.join(home, ".run"),
        "XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "GNOME",
    }
    for key, value in (extra or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return env


# Undoes a scenario's git_setup: back to the detached commit the copy was made at, scenario branches deleted
GIT_TEARDOWN = r"""
git checkout -q -f --detach "$(git rev-parse --verify -q refs/parity/base)"
git for-each-ref --format='%(refname:short)' refs/heads/ | xargs -r git branch -q -D
"""


def overlay(repo_copy, files):
    """Replace files in the repo copy for one scenario; returns what to put back."""
    originals = {}
    for rel, text in files.items():
        path = os.path.join(repo_copy, rel)
        with open(path, "rb") as f:
            originals[path] = (f.read(), os.stat(path).st_mode)
        with open(path, "w") as f:
            f.write(text)
    return originals


def restore(repo_copy, originals):
    for path, (data, mode) in originals.items():
        with open(path, "wb") as f:
            f.write(data)
        os.chmod(path, mode)


def run_in_pty(cmd, env, cwd, stdin_text, timeout=120, piped=False):
    """(output with \\r\\n turned into \\n, exit code); -9 if it had to be killed. With `piped`, input comes
    from a pipe instead of the terminal (as in scripts; prompts aren't shown then)."""
    master, slave = os.openpty()
    attrs = termios.tcgetattr(slave)
    attrs[3] &= ~(termios.ECHO | termios.ECHONL)
    termios.tcsetattr(slave, termios.TCSANOW, attrs)
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))
    # Its own process group (as a shell runs a command), not its own session: a session leader's exit would
    # send SIGHUP to background jobs (e.g. the installer's Download Assistant start) that survive in real use
    proc = subprocess.Popen(cmd, env=env, cwd=cwd, stdin=subprocess.PIPE if piped else slave, stdout=slave,
                            stderr=slave, preexec_fn=os.setpgrp)
    if piped:
        proc.stdin.write(stdin_text.encode())
        proc.stdin.close()
    elif stdin_text:
        os.write(master, stdin_text.encode())
    # Our end of the terminal stays open until the program has exited and its output has gone quiet (the
    # session log's tee finishes after Bash exits): Linux may drop unread output once the last writer closes.
    out, deadline, killed, quiet_since = bytearray(), time.monotonic() + timeout, False, None
    slave_open = True
    while True:
        if time.monotonic() > deadline and not killed:
            os.killpg(proc.pid, signal.SIGKILL)
            killed = True
        ready, _, _ = select.select([master], [], [], 0.1)
        if ready:
            try:
                data = os.read(master, 65536)
            except OSError:  # EIO: every process holding the terminal has gone
                break
            if not data:
                break
            out += data
            quiet_since = None
            continue
        if proc.poll() is None:
            continue
        quiet_since = quiet_since or time.monotonic()
        if slave_open and time.monotonic() - quiet_since > 0.5:
            os.close(slave)
            slave_open = False
        elif not slave_open and time.monotonic() - quiet_since > 5:
            break  # something still holds the terminal (e.g. a background process); stop waiting
    if slave_open:
        os.close(slave)
    try:  # background jobs still running (e.g. the Download Assistant watcher) mustn't outlive the scenario
        os.killpg(proc.pid, signal.SIGKILL)
    except OSError:
        pass
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
        for name in sorted(dirs):  # links to folders (folder mappings) are listed with their targets
            path = os.path.join(root, name)
            if os.path.islink(path):
                names.append(mask(f"{os.path.relpath(path, home)} -> {os.readlink(path)}", replacements))
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
    # A set: two sessions in the same second share a log file name, so their number depends on timing
    return sorted(set(names)), contents


def run_scenario(scenario, repo_copy, workdir):
    """Run one scenario in `repo_copy`; returns a dict of everything compared."""
    home = os.path.join(workdir, "home")
    shutil.rmtree(home, ignore_errors=True)
    os.makedirs(os.path.join(home, ".run"), mode=0o700)
    for rel, text in scenario.get("files", {}).items():
        if text is None:  # lets a scenario leave out one file of a shared set
            continue
        path = os.path.join(home, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text.replace("<HOME>", home))
    bindir = os.path.join(workdir, "fakebin")
    scenario_bin = os.path.join(workdir, "scenario-bin")  # the scenario's own fakes, ahead of the defaults
    shutil.rmtree(scenario_bin, ignore_errors=True)
    make_fakes(scenario_bin, scenario.get("fakes", {}), defaults=False)
    env = environment(home, scenario_bin + ":" + bindir, scenario.get("env"))
    cmd = [os.path.join(repo_copy, scenario.get("command", "torquio")), *scenario.get("args", [])]
    if shutil.which("unshare"):
        cmd = ["unshare", "--map-current-user", "--net", "--", *cmd]
    originals = overlay(repo_copy, scenario.get("repo_files", {}))
    if scenario.get("git_setup"):
        subprocess.run(["bash", "-ec", scenario["git_setup"]], cwd=repo_copy, check=True, capture_output=True)
    try:
        output, code = run_in_pty(cmd, env, home, scenario.get("input", ""), scenario.get("timeout", 120),
                                  scenario.get("piped", False))
    finally:
        if scenario.get("git_setup"):
            subprocess.run(["bash", "-c", GIT_TEARDOWN], cwd=repo_copy, capture_output=True)
        restore(repo_copy, originals)
    replacements = [(repo_copy, "<REPO>"), (home, "<HOME>"), (workdir, "<TMP>")]
    names, contents = snapshot(home, scenario.get("compare_files", []) + [".fake-calls"], replacements)
    calls = contents[".fake-calls"]
    if calls is not None:  # background work (e.g. a watcher, a dialog) makes some calls' order or count timing-dependent
        lines = [l for l in calls.splitlines() if not any(i in l for i in scenario.get("ignore_calls", []))]
        contents[".fake-calls"] = "\n".join(sorted(lines) if scenario.get("unordered_calls") else lines)
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
        try:
            make_copy(self.repo, self.base_ref, self.base)
            make_copy(self.repo, "HEAD", self.new, with_working_tree=True)
            make_fakes(os.path.join(self.tmp, "fakebin"))
        except BaseException:
            shutil.rmtree(self.tmp, ignore_errors=True)
            raise
        return self

    def __exit__(self, *exc):
        if self.keep:
            print(f"Kept {self.tmp}")
        else:
            shutil.rmtree(self.tmp, ignore_errors=True)
