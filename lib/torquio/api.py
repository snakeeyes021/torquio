"""`torquio api VERB`: the machine-readable interface for Torquio's GUI (docs/GUI.md). Prints JSON on stdout
and nothing else: no session log header, no colours, no prompts. The GUI runs it on the host (through
`flatpak-spawn --host` from its sandbox) and checks API_VERSION first.

Bump API_VERSION when a verb's output changes in a way an older GUI would misread; adding verbs or fields
doesn't need it."""
import json
import os
import stat
import sys

from . import config, container, engine, identity, paths, run

API_VERSION = 1


def version():
    code, describe = run.capture(["git", "-C", paths.repo_dir(), "describe", "--tags", "--always", "--dirty"])
    return {"api": API_VERSION, "torquio": describe.strip() if code == 0 else "", "repo": paths.repo_dir()}


def _char_device(path):
    try:
        return stat.S_ISCHR(os.stat(path).st_mode)
    except OSError:
        return False


def _ntsync():
    if os.path.exists("/dev/ntsync") or _char_device("/run/host/dev/ntsync"):
        return "active"
    return "dormant" if run.succeeds(["modinfo", "ntsync"]) else "unavailable"


def _engine(image):
    if not image:
        return {"source": "", "image": "", "update_available": False}
    from_image = engine.from_image(image)
    return {"source": "prebuilt" if from_image else "compiled", "image": image,
            "update_available": engine.outdated(image)}


def _pending_updates():
    if config.get_text("check_for_updates", "true") != "true":
        return 0
    code, out = run.capture(["git", "-C", paths.repo_dir(), "rev-list", "--count", "HEAD..@{u}"])
    return int(out.strip()) if code == 0 and out.strip().isdigit() else 0


def status():
    """What the Status Dashboard shows, as data."""
    listing = container.distrobox_list()
    exists = container.exists(listing)
    prefix = paths.prefix_dir()
    machine_id = identity.container_machine_id() if exists else ""
    data = {
        "container": {"name": paths.container_name(), "exists": exists,
                      "status": container.status(listing) if exists else ""},
        "engine": _engine(container.image() if exists else ""),
        "identity": ("stable" if machine_id and machine_id == identity.derived_machine_id()
                     else "container" if len(machine_id) == 32 else ""),
        "prefix": {"path": prefix, "exists": os.path.isdir(prefix),
                   "core_installed": os.path.isfile(os.path.join(prefix, ".torquio_core_installed"))},
        "ntsync": _ntsync(),
        "settings": {
            "manage_graphics": config.get_text("manage_graphics", "false") == "true",
            "manual_dpi": config.get_text("manual_dpi", "96"),
            "match_physical_dpi": config.get_text("match_physical_dpi", "false") == "true",
            "freetype_interpreter": config.get_text("freetype_interpreter", "40"),
            "ai_gpu": config.get_text("ai_gpu", "auto"),
            "check_for_updates": config.get_text("check_for_updates", "true") == "true",
        },
        "session_type": os.environ.get("XDG_SESSION_TYPE", ""),
        "updates_pending": _pending_updates(),
    }
    data["installed"] = exists and data["prefix"]["core_installed"]
    return data


VERBS = {"version": version, "status": status}


def main(args):
    """Returns the exit code: 0, or 2 for an unknown verb (with {"error": ...})."""
    verb = args[0] if args else ""
    if verb not in VERBS:
        json.dump({"error": f"unknown verb {verb!r}", "verbs": sorted(VERBS)}, sys.stdout)
        print()
        return 2
    json.dump(VERBS[verb](), sys.stdout, indent=None)
    print()
    return 0
