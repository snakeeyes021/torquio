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
MIN_API = 1
IN_FLATPAK = os.path.exists("/.flatpak-info")
HOME = os.path.expanduser("~")


class NotInstalled(Exception):
    """There's no Torquio on the host."""


class TooOld(Exception):
    """The host's Torquio predates the API this GUI needs (it can be updated)."""


class HostError(Exception):
    """A host command failed; the message is for the user."""


def command(cmd):
    """`cmd` as it has to run to reach the host."""
    return ["flatpak-spawn", "--host", *cmd] if IN_FLATPAK else list(cmd)


def run(cmd, timeout=60):
    """Run on the host without input; returns (exit code, stdout)."""
    try:
        p = subprocess.run(command(cmd), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, text=True, timeout=timeout)
    except FileNotFoundError:
        return 127, ""
    except subprocess.TimeoutExpired:
        return 124, ""
    return p.returncode, p.stdout


def spawn(cmd):
    """Start on the host and don't wait (launching Dorico and the like)."""
    subprocess.Popen(command(cmd), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


# Where the GUI downloads Torquio when the computer has none (the uninstaller leaves it alone)
APP_COPY = os.path.join(HOME, ".local/share/torquio-app")


def torquio():
    """The host's `torquio`: the link the installer puts in ~/.local/bin (the same path inside and outside the
    sandbox, which shares $HOME's path), else the copy the GUI downloaded before installing."""
    for path in (os.path.join(HOME, ".local/bin/torquio"), os.path.join(APP_COPY, "torquio")):
        if run(["test", "-x", path], timeout=10)[0] == 0:
            return path
    raise NotInstalled()


def launcher(name):
    """A Torquio launcher in ~/.local/bin (torquio-dorico, torquio-sam, torquio-sda-handler)."""
    return os.path.join(HOME, ".local/bin", name)


def api(verb, *args, timeout=120):
    """`torquio api VERB ARGS...` as data."""
    code, out = run([torquio(), "api", verb, *args], timeout=timeout)
    try:
        data = json.loads(out.strip().splitlines()[-1]) if out.strip() else None
    except (ValueError, IndexError):
        data = None
    if not isinstance(data, dict):
        if code == 124:
            raise HostError(f"Torquio took too long to answer ({verb}).")
        # Torquio before the API treats `api` as an unknown option
        raise TooOld()
    if code != 0:
        raise HostError(data.get("error", f"torquio api {verb} failed (exit code {code})"))
    return data


def check_version():
    """The host's `torquio api version`, if this GUI can use it (raises TooOld otherwise)."""
    data = api("version", timeout=30)
    if data.get("api", 0) < MIN_API:
        raise TooOld()
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

    def __init__(self, name, *args, on_event=None, on_done=None):
        self.name, self.args = name, args
        self.on_event, self.on_done = on_event, on_done
        self.code = None

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()
        return self

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
        if self.on_done:
            GLib.idle_add(lambda: self.on_done(code) and False)


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
