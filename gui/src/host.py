"""Running Torquio on the host. Everything Torquio does happens there (distrobox, the container, the Wine prefix,
the launchers in ~/.local/bin), so the app carries its own copy of Torquio, places it on the host (in
~/.local/share/torquio/app, silently, whenever the app's copy differs from the one there) and runs that copy:
through `flatpak-spawn --host` inside the Flatpak sandbox, directly otherwise. The app and the copy it runs are
always the same version (docs/GUI.md, "One app"). Torquio answers `torquio api VERB` with JSON, and
`torquio api task NAME` with one JSON event per line."""
import json
import os
import re
import subprocess
import sys
import tarfile
import threading
from gettext import gettext as _

from gi.repository import Gio, GLib

IN_FLATPAK = os.path.exists("/.flatpak-info")
HOME = os.path.expanduser("~")
# Torquio inside the app (gui/bundle.py puts it there)
BUNDLE = "/app/share/torquio/tree"
STAMP = ".torquio-app.json"
# Where the app places its copy on the host: in Torquio's data folder, with everything else Torquio keeps (the
# uninstaller leaves it until last). Its installers/ folder (installers the user chose) is kept each time the copy
# is replaced.
HOST_COPY = os.path.join(HOME, ".local/share/torquio/app")
# Where an early 0.7.0 build placed it; moved to HOST_COPY (with its installers) on the next start
OLD_HOST_COPY = os.path.join(HOME, ".local/share/torquio-app")
# For developing Torquio: run a checkout instead of the app's copy (e.g. in GNOME Builder's run environment)
DEV_REPO = os.environ.get("TORQUIO_HOST_REPO", "")

# The prerequisites' rules (lib/torquio/prereqs.py), from the bundled copy, as the app needs them before
# Torquio itself can run on the host
for _lib in (os.path.join(BUNDLE, "lib"), os.path.join(DEV_REPO, "lib") if DEV_REPO else ""):
    if _lib and os.path.isdir(_lib) and _lib not in sys.path:
        sys.path.insert(0, _lib)


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
        return 127, "", _("{} isn't available").format(command(cmd)[0])
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


def reach_host():
    """Raise HostError when host commands can't run at all (the app's permission to talk to the host is
    missing): the one start-up failure left for a normal install."""
    code, _out, err = run_full(["true"], timeout=20)
    if code != 0:
        detail = err.strip().splitlines()[-1] if err.strip() else _("exit code {}").format(code)
        raise HostError(_("This app can't run programs on this computer ({}). It needs permission to talk to "
                          "org.freedesktop.Flatpak.").format(detail))


def copy_dir():
    """The Torquio the app runs on the host: its own copy, or a developer's checkout (TORQUIO_HOST_REPO)."""
    return DEV_REPO or HOST_COPY


def torquio():
    return os.path.join(copy_dir(), "torquio")


def bundled_stamp():
    try:
        with open(os.path.join(BUNDLE, STAMP), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


# Replaces the host copy with the tar archive on stdin: unpacked next to it first, the user's installers moved
# over, then swapped in (the old copy goes only once the new one is in place)
PLACE = r'''
set -e
dest=$1; legacy=$2; parent=$(dirname "$dest"); mkdir -p "$parent"
# A copy where an early build put it moves here first (with its installers); only one copy of the app's
# own: a checkout someone keeps there (with .git) is left alone
if [ -d "$legacy" ] && [ ! -e "$legacy/.git" ] && [ -f "$legacy/.torquio-app.json" ] && [ ! -e "$dest" ]; then
    mv "$legacy" "$dest"
fi
new=$(mktemp -d "$parent/.torquio-app-new.XXXXXX")
trap 'rm -rf "$new"' EXIT
tar -x -C "$new" -f -
old=""
if [ -e "$dest" ]; then
    old="$parent/.torquio-app-old.$$"
    mv "$dest" "$old"
    if [ -d "$old/installers" ]; then rm -rf "$new/installers"; mv "$old/installers" "$new/installers"; fi
fi
if ! mv "$new" "$dest"; then [ -n "$old" ] && mv "$old" "$dest"; exit 1; fi
trap - EXIT
[ -n "$old" ] && rm -rf "$old"
# An early build's copy still there (both existed): keep its installers, then it goes
if [ -d "$legacy" ] && [ ! -e "$legacy/.git" ] && [ -f "$legacy/.torquio-app.json" ]; then
    if [ -d "$legacy/installers" ]; then mkdir -p "$dest/installers"; cp -an "$legacy/installers/." "$dest/installers/"; fi
    rm -rf "$legacy"
fi
exit 0
'''


def place_copy():
    """Make the host's copy the app's own (silently; only when the stamps differ). Returns True when it was
    replaced (the caller then refreshes the launchers and settings from it)."""
    if DEV_REPO:
        return False
    stamp = bundled_stamp()
    if not stamp:
        raise HostError(_("This build of the app doesn't contain Torquio (gui/bundle.py didn't run)."))
    code, out = run(["cat", os.path.join(HOST_COPY, STAMP)], timeout=20)
    legacy = run(["test", "-f", os.path.join(OLD_HOST_COPY, STAMP)], timeout=20)[0] == 0
    try:
        if code == 0 and json.loads(out) == stamp and not legacy:
            return False
    except ValueError:
        pass
    try:
        proc = subprocess.Popen(command(["sh", "-c", PLACE, "sh", HOST_COPY, OLD_HOST_COPY]), stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        with tarfile.open(fileobj=proc.stdin, mode="w|") as tar:
            for name in sorted(os.listdir(BUNDLE)):
                tar.add(os.path.join(BUNDLE, name), arcname=name)
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "replace")
        code = proc.wait(timeout=300)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise HostError(_("Couldn't put Torquio's files on this computer ({}).").format(e))
    if code != 0:
        raise HostError(_("Couldn't put Torquio's files on this computer")
                        + (f":\n{_last_lines(err)}" if err.strip() else "."))
    return True


# What's on the host, found with the shell alone (before Torquio, which needs Python, can run)
FACTS = r'''
PATH="$HOME/.local/bin:$PATH"
have() { command -v "$1" >/dev/null 2>&1 && echo 1 || echo 0; }
py=0
if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then py=1; fi
echo "python=$py"
echo "distrobox=$(have distrobox)"
echo "podman=$(have podman)"
echo "docker=$(have docker)"
echo "ostree=$([ -e /run/ostree-booted ] && echo 1 || echo 0)"
echo "transactional=$([ -x /usr/sbin/transactional-update ] && [ ! -w /usr ] && echo 1 || echo 0)"
echo "ublue=$([ -d /usr/share/ublue-os ] && echo 1 || echo 0)"
echo "pkexec=$(have pkexec)"
echo "---"
cat /etc/os-release 2>/dev/null || cat /usr/lib/os-release 2>/dev/null
'''


def facts():
    """{"python", "distrobox", "podman", "docker", "ostree", "transactional", "pkexec": bool, "os": os-release
    text, "family": the prerequisites' family, "missing": keys of what's needed and not there}."""
    from torquio import prereqs
    code, out = run(["sh", "-c", FACTS], timeout=30)
    head, _, os_text = out.partition("---\n")
    data = {"os": os_text}
    for line in head.splitlines():
        key, _, value = line.partition("=")
        data[key] = value.strip() == "1"
    info = prereqs.parse_os_release(os_text)
    data["name"] = info.get("PRETTY_NAME") or info.get("NAME") or ""
    data["family"] = prereqs.family(info, ostree=data.get("ostree", False),
                                    transactional=data.get("transactional", False), ublue=data.get("ublue", False))
    data["missing"] = prereqs.missing(data.get("python", False), data.get("distrobox", False),
                                      data.get("podman", False), data.get("docker", False))
    return data


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
            raise HostError(_("Torquio took too long to answer ({}).").format(verb))
        detail = _last_lines(err) or _last_lines(out)
        raise HostError(_("torquio api {verb} failed (exit code {code})").format(verb=verb, code=code)
                        + (f":\n{detail}" if detail else "."))
    if code != 0:
        raise HostError(data.get("error") or
                        _("torquio api {verb} failed (exit code {code})").format(verb=verb, code=code))
    return data


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

    def __init__(self, name, *args, on_event=None, on_done=None, argv=None):
        """`argv`: run that command on the host instead of a Torquio task (installing what Torquio needs, before
        Torquio can run); each line of its output becomes a log event, and its exit code the result."""
        self.name, self.args, self.argv = name, args, argv
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
            if self.argv:
                proc = subprocess.Popen(command(self.argv), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True, errors="replace", bufsize=1)
                for line in proc.stdout:
                    GLib.idle_add(self._deliver, {"event": "log", "text": line.rstrip("\n")})
                code = proc.wait()
                self.code = code
                GLib.idle_add(self._finished, code)
                return
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
        except OSError as e:
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
