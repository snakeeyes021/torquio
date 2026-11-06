"""Developer tool for the copy review (see copyhints.py): a canned Torquio, so every screen and state can be shown
without running anything on the computer. Used in hint mode, or alone with TORQUIO_COPY_FAKE=1.

TORQUIO_COPY_STATE picks a starting state: comma-separated presets (PRESETS below), e.g. "fresh" or
"nodorico,x11". DATA (the answers per verb), ERRORS (verb -> error message) and KNOBS can also be changed while
the app runs; refresh the window afterwards."""
import copy
import json
import os
import threading
import time

from gi.repository import GLib

from . import copyhints, host

HOME = os.path.expanduser("~")
DOWNLOADS = os.path.join(HOME, "Downloads")
PREFIX = os.path.join(HOME, ".local/share/torquio/prefix")

BASE = {
    "version": {"api": 2, "torquio": "v0.7.0", "branch": "main", "repo": os.path.join(HOME, "dev/torquio")},
    "status": {
        "installed": True, "updates_pending": 0, "session_type": "wayland", "ntsync": "dormant",
        "apps": {"dorico": True, "activation_manager": True, "download_assistant": True, "noteperformer": True,
                 "cantai": True},
        "engine": {"source": "prebuilt", "image": "ghcr.io/example/torquio-wine:10", "update_available": True},
        "container": {"exists": True, "name": "torquio", "status": "Up 2 hours"},
        "prefix": {"path": PREFIX},
        "settings": {"manage_graphics": True, "manual_dpi": "96", "match_physical_dpi": False,
                     "freetype_interpreter": "40", "ai_gpu": "auto", "check_for_updates": True},
    },
    "running": {"running": True},
    "display": {"session_type": "wayland", "wine_dpi": 144, "restorable": {"current": "2", "original": "0"},
                "graphics": {"de": "GNOME", "connector": "eDP-1", "width": 2880, "height": 1800, "scale": 1.5,
                             "physical_dpi": 218, "target_wine_dpi": 144}},
    "folders": {"drives": [{"letter": "D:", "target": os.path.join(HOME, "Music/Scores")}],
                "shortcuts": [{"name": "Parts", "target": os.path.join(HOME, "Documents/Parts"),
                               "path": PREFIX + "/drive_c/users/me/Desktop/Parts"}]},
    "keycommands": {"dorico_files": ["keycommands_en.json"],
                    "backups": [os.path.join(DOWNLOADS, "Dorico_KeyCommands_2026-10-30.zip")],
                    "exported": os.path.join(DOWNLOADS, "Dorico_KeyCommands_2026-11-05.zip")},
    "gpus": {"automatic": "NVIDIA GeForce RTX 4070", "setting": "auto", "engine_support": True,
             "vkd3d": "v2.14", "cantai": True, "nvidia": {"host": True, "enabled": False},
             "gpus": [{"name": "NVIDIA GeForce RTX 4070"}, {"name": "AMD Radeon 780M"}]},
    "prereqs": {"distrobox": True, "container_manager": "podman", "session_type": "wayland", "ntsync": "dormant",
                "installers_dir": DOWNLOADS,
                "installers": {"sda": os.path.join(DOWNLOADS, "Steinberg_Download_Assistant_1.38_Installer_win.exe"),
                               "mediabay": "", "noteperformer": "", "cantai": ""}},
    "updates": {"local_changes": False,
                "commits": [f"Change number {n} in this update" for n in range(1, 16)]},
    "guards": {"steinberg_active": ["Dorico Pro 6"], "steinberg_unknown": False,
               "plugins": [{"name": "Cantai", "where": "Cantai"}],
               "projects": [PREFIX + f"/drive_c/users/me/Documents/Project {n}.dorico" for n in range(1, 8)],
               "restorable": {"current": "2", "original": "0"}},
}

DATA = copy.deepcopy(BASE)
ERRORS = {}  # verb -> the error message Torquio answers with
KNOBS = {
    "host": "ok",          # ok | unreachable | missing (no Torquio) | tooold | slow | crash
    "git": True, "clone": True, "copy": True, "launcher": True,
    "update_old": 0,       # update_old_torquio's script exit code (2, 3, 4, 5 or another failure)
    "still_old": False,    # after updating, Torquio is still too old
    "task_fail": False,    # tasks fail at their last step
    "task_hold": None,     # tasks stop (keep running) after this many steps
    "wine_code": 0,        # Wine programs' exit code
    "step_ms": 150,
    "host_error": "Portal call failed: org.freedesktop.Flatpak isn't allowed",  # "" or "no-helper" too
    "after_clone": "ok",   # the host state once Torquio is downloaded
    "delay": {},           # seconds before an answer: verb, "clone", "update_old" or "copy" -> seconds
}


def _wait(what):
    time.sleep(KNOBS["delay"].get(what, 0))

# The steps each task shows (the texts the computer's Torquio sends, lib/torquio/api.py)
TASK_STEPS = {
    "install": ["Setting up the container", "Getting the Wine engine",
                "Preparing Windows: fonts, .NET and runtimes (the longest step)",
                "Installing Steinberg's components and your plug-ins", "Adding Dorico to your desktop",
                "Mapping your folder"],
    "update": ["Downloading the update", "Refreshing launchers and settings"],
    "fix-icons": ["Icons and menu entries", "Wine prefix settings", "Launchers"],
    "engine-update": ["Downloading the Wine engine", "Replacing the container"],
    "engine-rebuild": ["Compiling the Wine engine (20-40 minutes)", "Compiling the Wine engine"],
    "setup-gpu": ["Re-creating the container with NVIDIA access", "Setting up GPU access"],
    "uninstall": ["Restoring your desktop's scaling setting", "Removing the container", "Removing Torquio's data",
                  "Removing launchers and file types"],
}


def _fresh():
    DATA["status"]["installed"] = False


def _nodorico():
    s = DATA["status"]
    s["apps"].update(dorico=False, noteperformer=False, cantai=False)
    s["engine"].update(source="", update_available=False)
    s["container"]["exists"] = False
    s["ntsync"] = "unavailable"
    DATA["folders"] = {"drives": [], "shortcuts": []}
    DATA["keycommands"].update(dorico_files=[], backups=[])
    DATA["gpus"].update(automatic="", gpus=[], engine_support=False, vkd3d="", cantai=False,
                        nvidia={"host": False, "enabled": False})
    DATA["guards"].update(steinberg_active=[], plugins=[], projects=[], restorable=None)


def _x11():
    DATA["status"]["session_type"] = "x11"
    DATA["status"]["settings"]["manage_graphics"] = False
    DATA["prereqs"]["session_type"] = "x11"
    DATA["display"]["session_type"] = "x11"
    DATA["status"]["engine"].update(source="compiled", update_available=False)
    DATA["status"]["ntsync"] = "active"
    DATA["gpus"].update(setting="off", nvidia={"host": True, "enabled": True})


def _manual():
    DATA["status"]["settings"].update(manage_graphics=False, freetype_interpreter="35", manual_dpi="120")


def _nothing():
    """The setup assistant on a computer with nothing it needs."""
    DATA["prereqs"].update(distrobox=False, container_manager="", ntsync="unavailable",
                           installers={"sda": "", "mediabay": "", "noteperformer": "", "cantai": ""})


def _everything():
    DATA["prereqs"]["ntsync"] = "active"
    DATA["prereqs"]["installers"] = {k: os.path.join(DOWNLOADS, f"{k}-installer.exe")
                                     for k in ("sda", "mediabay", "noteperformer", "cantai")}


def _unsure():
    DATA["guards"].update(steinberg_active=[], plugins=[], steinberg_unknown=True)


PRESETS = {"fresh": _fresh, "nodorico": _nodorico, "x11": _x11, "manual": _manual, "nothing": _nothing,
           "everything": _everything, "unsure": _unsure,
           "missing": lambda: KNOBS.update(host="missing"), "tooold": lambda: KNOBS.update(host="tooold"),
           "unreachable": lambda: KNOBS.update(host="unreachable"), "slow": lambda: KNOBS.update(host="slow"),
           "crash": lambda: KNOBS.update(host="crash"), "fail": lambda: KNOBS.update(task_fail=True)}


def preset(names):
    for name in filter(None, (n.strip() for n in names.split(","))):
        PRESETS[name]()


def _answer(verb, args):
    if verb in ERRORS:
        return 1, json.dumps({"error": copyhints.label(ERRORS[verb])}), ""
    data = copy.deepcopy(DATA.get(verb, {}))
    if verb == "folders" and args[:1] == ["map"]:
        DATA["folders"]["drives"].append({"letter": "E:", "target": args[1]})
        data = copy.deepcopy(DATA["folders"])
    elif verb == "folders" and args[:1] == ["unmap"]:
        f = DATA["folders"]
        f["drives"] = [d for d in f["drives"] if d["letter"] != args[2]]
        f["shortcuts"] = [s for s in f["shortcuts"] if s["path"] != args[2]]
        data = copy.deepcopy(f)
    elif verb == "settings" and args[:1] == ["set"]:
        value = args[2] == "true" if args[2] in ("true", "false") else args[2]
        DATA["status"]["settings"][args[1]] = value
    return 0, json.dumps(data), ""


def run_full(cmd, timeout=60):
    cmd = list(cmd)
    state = KNOBS["host"]
    if cmd == ["true"]:
        if state != "unreachable":
            return 0, "", ""
        if KNOBS["host_error"] == "no-helper":
            return 127, "", host._("{} isn't available").format("flatpak-spawn")
        return 1, "", KNOBS["host_error"]
    if cmd[:2] == ["test", "-x"]:
        if cmd[2].endswith("/torquio"):
            return (1, "", "") if state in ("missing", "unreachable") else (0, "", "")
        return (0, "", "") if KNOBS["launcher"] else (1, "", "")
    if cmd[:2] == ["test", "-d"]:
        return 1, "", ""
    if cmd[:3] == ["sh", "-c", "command -v git"]:
        return (0, "/usr/bin/git", "") if KNOBS["git"] else (1, "", "")
    if cmd[:1] == ["git"]:
        _wait("clone")
        if KNOBS["clone"]:
            KNOBS["host"] = KNOBS["after_clone"]
            return 0, "", ""
        return 128, "", "fatal: unable to access GitHub"
    if cmd[:3] == ["sh", "-c", host.UPDATE_OLD]:
        _wait("update_old")
        code = KNOBS["update_old"]
        if code == 0 and not KNOBS["still_old"]:
            KNOBS["host"] = "ok"
        return code, "", "error: the post-update step stopped here"
    if cmd[:2] == ["sh", "-c"]:
        _wait("copy")
        return (0, "", "") if KNOBS["copy"] else (1, "", "")
    if len(cmd) > 2 and cmd[1] == "api":
        verb, args = cmd[2], cmd[3:]
        _wait(verb)
        if state == "slow":
            return 124, "", ""
        if state == "crash":
            return 1, "", "Traceback (most recent call last):\nOSError: [Errno 5] Input/output error"
        if state == "tooold" and verb == "version":
            return 2, "Usage: torquio [OPTION]", ""
        return _answer(verb, args)
    return 0, "", ""


def _task_run(self):
    def deliver(event):
        GLib.idle_add(self._deliver, event)
    steps = [] if self.name in ("wine", "ntsync", "logs") else TASK_STEPS.get(self.name, [])
    code = 0
    for i, step in enumerate(steps):
        if KNOBS["task_hold"] is not None and i >= KNOBS["task_hold"]:
            return  # keeps running
        deliver({"event": "phase", "text": copyhints.label(step)})
        deliver({"event": "log", "text": f"(the task's own output, step {i + 1})"})
        time.sleep(KNOBS["step_ms"] / 1000)
    if self.name == "logs":
        deliver({"event": "result", "path": os.path.join(DOWNLOADS, "torquio-logs-2026-11-05.zip")})
    if self.name == "wine":
        code = KNOBS["wine_code"]
    elif KNOBS["task_fail"]:
        deliver({"event": "log", "text": "(the task's own output: where it stopped)"})
        code = 1
    deliver({"event": "done", "code": code})
    self.code = code
    GLib.idle_add(self._finished, code)


def _start_task(self):
    if self.name != "wine":
        host.Task.running.add(self)
    threading.Thread(target=_task_run, args=(self,), daemon=True).start()
    return self


def _finished(self, code):
    host.Task.running.discard(self)
    if self.on_done:
        self.on_done(code)
    return False


def install():
    """Replace everything in host.py that reaches the computer."""
    host.run_full = run_full
    host.spawn = lambda cmd: None
    host.show_in_files = lambda path: None
    host.open_folder = lambda path: None
    host.host_path = lambda path: path
    # The app's copy of Torquio isn't placed, and the computer is "Fedora with everything"
    host.place_copy = lambda: False
    host.facts = lambda: {"python": True, "distrobox": True, "podman": True, "docker": False, "ostree": False,
                          "transactional": False, "ublue": False, "pkexec": True, "os": "",
                          "name": "Fedora Linux 44 (Workstation Edition)", "family": "dnf", "missing": []}
    host.Task.start = _start_task
    host.Task._finished = _finished
    preset(os.environ.get("TORQUIO_COPY_STATE", ""))
