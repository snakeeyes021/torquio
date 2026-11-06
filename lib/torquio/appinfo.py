"""Which copy of Torquio this is. The app places its own copy on the host (docs/GUI.md, "One app"), with a stamp
file naming its version; a developer's git checkout has none and describes itself with git."""
import json
import os

from . import paths, run

STAMP = ".torquio-app.json"


def stamp():
    """The app copy's stamp ({"version", "hash"}), or {} in a git checkout."""
    try:
        with open(os.path.join(paths.repo_dir(), STAMP), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def is_app_copy():
    """Whether this is the copy the app placed on the host (updated with the app, not with git)."""
    return bool(stamp())


def version():
    """The app's version for the app's copy, else `git describe` of the checkout ("" if neither)."""
    s = stamp()
    if s.get("version"):
        return s["version"]
    code, out = run.capture(["git", "-C", paths.repo_dir(), "describe", "--tags", "--always", "--dirty"])
    return out.strip() if code == 0 else ""


def branch():
    """The checkout's branch ("" for the app's copy)."""
    if is_app_copy():
        return ""
    code, out = run.capture(["git", "-C", paths.repo_dir(), "rev-parse", "--abbrev-ref", "HEAD"])
    return out.strip() if code == 0 else ""
