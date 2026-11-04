"""Running Torquio on the host. Everything Torquio does happens there (distrobox, the container, the Wine prefix,
the launchers in ~/.local/bin), so the GUI drives the host's copy of Torquio: through `flatpak-spawn --host`
inside the Flatpak sandbox, directly otherwise. Torquio answers `torquio api VERB` with JSON, and
`torquio api task NAME` with one JSON event per line (docs/GUI.md)."""
import json
import os
import re
import subprocess
import threading

from gi.repository import Gio, GLib

# The oldest `torquio api` this GUI understands
MIN_API = 2
IN_FLATPAK = os.path.exists("/.flatpak-info")
HOME = os.path.expanduser("~")


class NotInstalled(Exception):
    """There's no Torquio on the host."""


class TooOld(Exception):
    """The host's Torquio predates the API this GUI needs (it can be updated)."""

    def __init__(self, message="The Torquio on this computer is older than this app. Update it first."):
        super().__init__(message)


class HostError(Exception):
    """A host command failed; the message is for the user."""


def command(cmd):
    """`cmd` as it has to run to reach the host."""
    return ["flatpak-spawn", "--host", *cmd] if IN_FLATPAK else list(cmd)


def run_full(cmd, timeout=60):
    """Run on the host without input; returns (exit code, stdout, stderr)."""
    try:
        p = subprocess.run(command(cmd), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True, errors="replace", timeout=timeout)
    except FileNotFoundError:
        return 127, "", f"{command(cmd)[0]} isn't available"
    except subprocess.TimeoutExpired:
        return 124, "", ""
    return p.returncode, p.stdout, p.stderr


def run(cmd, timeout=60):
    """Run on the host without input; returns (exit code, stdout)."""
    code, out, _err = run_full(cmd, timeout)
    return code, out


def spawn(cmd):
    """Start on the host and don't wait (launching Dorico and the like)."""
    subprocess.Popen(command(cmd), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


# Where the GUI downloads Torquio when the computer has none (the uninstaller leaves it alone)
APP_COPY = os.path.join(HOME, ".local/share/torquio-app")
# The last Torquio checkout the GUI talked to, remembered so the GUI still finds it if its link in ~/.local/bin is
# gone (the uninstaller removes it), instead of offering to download a second copy
KNOWN_REPO = os.path.join(GLib.get_user_config_dir(), "torquio-gui", "repo")


def _known_repo():
    try:
        with open(KNOWN_REPO) as f:
            return f.read().strip()
    except OSError:
        return ""


def _remember_repo(repo):
    if repo and repo != _known_repo():
        try:
            os.makedirs(os.path.dirname(KNOWN_REPO), exist_ok=True)
            with open(KNOWN_REPO, "w") as f:
                f.write(repo + "\n")
        except OSError:
            pass


def reach_host():
    """Raise HostError when host commands can't run at all (no permission to talk to the host, say)."""
    code, _out, err = run_full(["true"], timeout=20)
    if code != 0:
        raise HostError("This app can't run programs on this computer"
                        + (f" ({err.strip().splitlines()[-1]})" if err.strip() else f" (exit code {code})")
                        + ". It needs permission to talk to org.freedesktop.Flatpak.")


def torquio():
    """The host's `torquio`: the link the installer puts in ~/.local/bin (the same path inside and outside the
    sandbox, which shares $HOME's path), else the checkout the GUI last used, else the copy it downloaded."""
    known = _known_repo()
    candidates = [os.path.join(HOME, ".local/bin/torquio")] + ([os.path.join(known, "torquio")] if known else []) \
        + [os.path.join(APP_COPY, "torquio")]
    for path in candidates:
        if run(["test", "-x", path], timeout=10)[0] == 0:
            return path
    reach_host()
    raise NotInstalled()


def launcher(name):
    """A Torquio launcher in ~/.local/bin (torquio-dorico, torquio-sam, torquio-sda-handler)."""
    return os.path.join(HOME, ".local/bin", name)


def _last_lines(text, n=3):
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return "\n".join(lines[-n:])


def api(verb, *args, timeout=120):
    """`torquio api VERB ARGS...` as data."""
    code, out, err = run_full([torquio(), "api", verb, *args], timeout=timeout)
    try:
        data = json.loads(out.strip().splitlines()[-1]) if out.strip() else None
    except (ValueError, IndexError):
        data = None
    if not isinstance(data, dict):
        if code == 124:
            raise HostError(f"Torquio took too long to answer ({verb}).")
        # A Torquio from before the API treats `api` as an unknown option and prints its usage; anything else
        # (a crash, a missing Python) is an error to show as it is
        if verb == "version" and code != 127 and "Traceback" not in err and "Traceback" not in out:
            raise TooOld()
        detail = _last_lines(err) or _last_lines(out)
        raise HostError(f"torquio api {verb} failed (exit code {code})" + (f":\n{detail}" if detail else "."))
    if code != 0:
        raise HostError(data.get("error", f"torquio api {verb} failed (exit code {code})"))
    return data


def check_version():
    """The host's `torquio api version`, if this GUI can use it (raises TooOld otherwise)."""
    data = api("version", timeout=30)
    if data.get("api", 0) < MIN_API:
        raise TooOld()
    _remember_repo(data.get("repo", ""))
    return data


# Updating a Torquio too old for this GUI's API, the way `torquio -u` does it: fast-forward the host's checkout
# to GitHub's version, then let the new copy refresh launchers and settings (its own --post-update).
# Exit codes: 2 no checkout, 3 local changes, 5 no upstream branch, 4 fetch or merge failed, else --post-update's.
UPDATE_OLD = r'''
repo=$(dirname "$(readlink -f "$1")") && cd "$repo" && git rev-parse --git-dir >/dev/null 2>&1 || exit 2
[ -z "$(git status --porcelain --untracked-files=no)" ] || exit 3
git rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1 || exit 5
old=$(git rev-parse HEAD) && git fetch --quiet && git merge --ff-only --quiet '@{u}' || exit 4
exec ./torquio --post-update "$old" </dev/null
'''


def update_old_torquio():
    """Update the host's Torquio when it predates this GUI's API (raises HostError with the reason), then check
    that the update was enough."""
    code, _out, err = run_full(["sh", "-c", UPDATE_OLD, "sh", torquio()], timeout=900)
    if code == 2:
        raise HostError("The Torquio on this computer isn't a git checkout, so it can't update itself.")
    if code == 3:
        raise HostError("Torquio's files were changed on this computer, so it can't update itself. Run "
                        "torquio -u in a terminal to see what changed.")
    if code == 5:
        raise HostError("The Torquio on this computer is on a branch that doesn't follow GitHub, so it can't update "
                        "itself. Switch it to main (git checkout main) and try again.")
    if code in (4, 124):
        raise HostError("Torquio couldn't be updated from GitHub. Check your internet connection and try again.")
    if code != 0:
        detail = _last_lines(err)
        raise HostError("Torquio was updated, but refreshing its launchers and settings failed"
                        + (f":\n{detail}" if detail else ".") + "\nRun torquio -u in a terminal to finish.")
    try:
        check_version()
    except TooOld:
        raise TooOld("Torquio is updated, but its newest version is still older than this app. A newer Torquio "
                     "should follow soon; until then, use the terminal (torquio).") from None
    return code


def in_background(work, done):
    """Run work() in a thread (host commands take a while), then done(result, error) on the main loop."""
    def thread():
        try:
            result, error = work(), None
        except Exception as e:  # handed to `done`, which shows it
            result, error = None, e
        GLib.idle_add(lambda: done(result, error) and False)
    threading.Thread(target=thread, daemon=True).start()


class Task:
    """A long job on the host (`torquio api task NAME ARGS...`). Its events arrive on the main loop:
    on_event(event dict) for each one, and finally on_done(exit code). Closing the window that shows it doesn't
    stop it."""

    # Tasks that change the installation, running now (Wine's tools aren't counted: they stay open)
    running = set()

    def __init__(self, name, *args, on_event=None, on_done=None):
        self.name, self.args = name, args
        self.on_event, self.on_done = on_event, on_done
        self.code = None

    @classmethod
    def busy(cls):
        """The name of a running task that changes the installation, or None."""
        return next(iter(cls.running), None)

    def start(self):
        if self.name != "wine":
            Task.running.add(self)
        # The app keeps running until the task has finished, even with its window closed, so the task's
        # `flatpak-spawn` isn't torn down with the sandbox halfway
        app = Gio.Application.get_default() if self.name != "wine" else None
        if app:
            app.hold()
        threading.Thread(target=self._run, daemon=True).start()
        return self

    def _finished(self, code):
        Task.running.discard(self)
        app = Gio.Application.get_default() if self.name != "wine" else None
        if app:
            app.release()
        if self.on_done:
            self.on_done(code)
        return False

    def _deliver(self, event):
        if self.on_event:
            self.on_event(event)
        return False

    def _run(self):
        code = 1
        try:
            proc = subprocess.Popen(command([torquio(), "api", "task", self.name, *self.args]),
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    text=True, bufsize=1)
            for line in proc.stdout:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get("event") == "done":
                    code = event.get("code", 1)
                GLib.idle_add(self._deliver, event)
            proc.wait()
        except (OSError, NotInstalled) as e:
            GLib.idle_add(self._deliver, {"event": "log", "text": str(e)})
        self.code = code
        GLib.idle_add(self._finished, code)


DOC_PATH = re.compile(r"^/run/user/\d+/doc/([^/]+)(/.*)?$")


def host_path(path):
    """The host's path for a file or folder chosen in a file dialog. Inside the sandbox the portal hands out
    /run/user/UID/doc/ID/NAME; Torquio on the host needs the real path, which the Documents portal knows."""
    m = DOC_PATH.match(path or "")
    if not m:
        return path
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        reply = bus.call_sync("org.freedesktop.portal.Documents", "/org/freedesktop/portal/documents",
                              "org.freedesktop.portal.Documents", "GetHostPaths",
                              GLib.Variant("(as)", ([m.group(1)],)), GLib.VariantType("(a{say})"),
                              Gio.DBusCallFlags.NONE, 5000, None)
        paths = reply.unpack()[0]
        found = paths.get(m.group(1))
        if found:
            return bytes(found).rstrip(b"\0").decode("utf-8", "surrogateescape")
    except GLib.Error:
        pass
    return path


def show_in_files(path):
    """Show a file in the host's file manager (selected), or open a folder."""
    uri = GLib.filename_to_uri(path, None)
    if os.path.isdir(path) and not IN_FLATPAK:
        spawn(["gio", "open", uri])
        return
    spawn(["gdbus", "call", "--session", "--dest", "org.freedesktop.FileManager1",
           "--object-path", "/org/freedesktop/FileManager1", "--method", "org.freedesktop.FileManager1.ShowItems",
           f"['{uri}']", ""])


def open_folder(path):
    spawn(["gio", "open", GLib.filename_to_uri(path, None)])
