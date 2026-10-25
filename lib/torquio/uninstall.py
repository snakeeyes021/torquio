"""Removing Torquio: what the uninstaller checks before deleting anything, and the leftovers it cleans up."""
import fnmatch
import glob
import os
import re
import shutil

from . import folders, paths, run

# Projects in these parts of the prefix are Dorico's own (examples, tutorials, autosave data), not the user's
PROJECT_SEARCH_SKIPS = ["*/Program Files*", "*/ProgramData", "*/windows", "*/AppData",
                        "*/users/Public/Documents/Dorico Example Projects"]

DESKTOP_FILES = ["Dorico.desktop", "Dorico Audio Engine.desktop", "Steinberg Activation Manager.desktop",
                 "Steinberg Download Assistant.desktop", "wine-extension-dorico.desktop",
                 "wine-extension-vstsound.desktop", "wine-extension-slm.desktop"]
LAUNCHERS = ["torquio", "torquio-dorico", "torquio-sam", "torquio-sda-handler", "torquio_graphics.py"]
ICONS = ["torquio-dorico.png", "torquio-dorico-project.png", "torquio-dorico-audioengine.png", "torquio-sda.png",
         "torquio-sam.png"]
MIME_PACKAGES = ["application-x-dorico.xml", "x-wine-extension-dorico.xml", "x-wine-extension-vstsound.xml",
                 "x-wine-extension-slm.xml"]
DEFAULT_APP = re.compile(r"^[^=]+=(Dorico|Steinberg Download Assistant|Steinberg Activation Manager|Dorico Audio Engine)\.desktop;?$")
WINDOWS_SHORTCUTS = ["Activation Manager.lnk", "Steinberg Activation Manager.lnk", "Dorico*.lnk", "HALion*.lnk",
                     "Groove Agent*.lnk", "Steinberg Library Manager.lnk"]


def _walk(top):
    """(path, entry) below `top` in `find` order (directory order, depth first, symlinks not followed)."""
    try:
        entries = list(os.scandir(top))
    except OSError:
        return
    for entry in entries:
        yield entry
        if entry.is_dir(follow_symlinks=False) and not _skipped(entry.path):
            yield from _walk(entry.path)


def _skipped(path):
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in PROJECT_SEARCH_SKIPS)


def prefix_projects():
    """Dorico projects saved inside the Wine prefix (the prefix's Documents etc. link to the host's own folders,
    which deleting the prefix doesn't touch, so links aren't followed)."""
    found = []
    for entry in _walk(os.path.join(paths.prefix_dir(), "drive_c")):
        if _skipped(entry.path):
            continue
        if entry.is_file(follow_symlinks=False) and entry.name.lower().endswith(".dorico"):
            found.append(entry.path)
    return found


def _rm(path):
    """rm -f"""
    try:
        if os.path.islink(path) or not os.path.isdir(path):
            os.remove(path)
    except FileNotFoundError:
        pass
    except OSError:
        pass


def _rm_rf(path):
    if os.path.islink(path) or (os.path.lexists(path) and not os.path.isdir(path)):
        _rm(path)
    else:
        shutil.rmtree(path, ignore_errors=True)


def _mentions(path, needles):
    """grep -q -F -e NEEDLE... PATH"""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return False
    return any(n.encode() in line for line in data.split(b"\n") for n in needles)


def torquio_dir_patterns():
    """Torquio's data and cache directories, also by their real path (e.g. /var/home), for finding launchers
    Wine created for Torquio's prefixes."""
    data, cache = paths.data_dir(), paths.cache_dir()
    return [data, cache, os.path.realpath(data), os.path.realpath(cache)]


def remove_data():
    _rm_rf(paths.data_dir())
    _rm_rf(paths.cache_dir())
    _rm_rf(os.path.join(paths.home(), ".config/torquio"))


def remove_integrations():
    home = paths.home()
    for name in LAUNCHERS:
        _rm(os.path.join(home, ".local/bin", name))
    apps = os.path.join(home, ".local/share/applications")
    for name in DESKTOP_FILES:
        _rm(os.path.join(apps, name))
    for path in glob.glob(os.path.join(glob.escape(apps), "wine-protocol-net-steinberg-*.desktop")):
        _rm(path)
    needles = torquio_dir_patterns()

    # Leftovers of Wine's menu builder (Torquio disables it, but older versions and some setup steps didn't):
    # 1. launchers pointing into Torquio's data or cache directory, with the file types they registered
    candidates = []
    try:
        candidates += [e.path for e in os.scandir(apps) if fnmatch.fnmatchcase(e.name, "wine-*.desktop")]
    except OSError:
        pass
    wine_menu = os.path.join(apps, "wine")
    for root, dirs, files in os.walk(wine_menu):
        candidates += [os.path.join(root, f) for f in files + dirs if fnmatch.fnmatchcase(f, "*.desktop")]
    for launcher in candidates:
        if not _mentions(launcher, needles):
            continue
        name = os.path.basename(launcher)[:-len(".desktop")]
        _rm(launcher)
        if name.startswith("wine-extension-"):
            _rm(os.path.join(home, ".local/share/mime/packages", f"x-wine-extension-{name[len('wine-extension-'):]}.xml"))
    for root, dirs, files in os.walk(wine_menu, topdown=False):
        try:
            os.rmdir(root)
        except OSError:
            pass
    # 2. Wine menu entries whose launcher no longer exists (their desktop file ID is the launcher's path under
    #    applications/ with "/" replaced by "-")
    launcher_ids = set()
    for root, dirs, files in os.walk(wine_menu):
        launcher_ids |= {os.path.relpath(os.path.join(root, f), apps).replace("/", "-")
                         for f in files + dirs if fnmatch.fnmatchcase(f, "*.desktop")}
    merged = os.path.join(home, ".config/menus/applications-merged")
    for menu in sorted(glob.glob(os.path.join(glob.escape(merged), "wine-*.menu"))):
        if not os.path.isfile(menu):
            continue
        try:
            with open(menu, errors="replace") as f:
                m = re.search(r"<Filename>([^<\n]*)</Filename>", f.read())
        except OSError:
            m = None
        if not m or not m.group(1) or m.group(1) not in launcher_ids:
            _rm(menu)
    # 3. Wine menu folders no remaining menu entry uses
    menus = glob.glob(os.path.join(glob.escape(merged), "wine-*.menu"))
    directories = os.path.join(home, ".local/share/desktop-directories")
    for directory in sorted(glob.glob(os.path.join(glob.escape(directories), "wine-*.directory"))):
        if not os.path.isfile(directory):
            continue
        needle = [f"<Directory>{os.path.basename(directory)}</Directory>"]
        if not any(_mentions(m, needle) for m in menus):
            _rm(directory)

    for name in ICONS:
        _rm(os.path.join(home, ".local/share/icons/hicolor/256x256/apps", name))
    for name in MIME_PACKAGES:
        _rm(os.path.join(home, ".local/share/mime/packages", name))
    # Generated from Wine's .dorico file type; update-mime-database leaves it behind once its package is gone
    _rm_rf(os.path.join(home, ".local/share/mime/dorico"))
    # Default-application entries pointing at Torquio's launchers
    for path in (os.path.join(home, ".config/mimeapps.list"), os.path.join(apps, "mimeapps.list")):
        if os.path.isfile(path):
            remove_default_apps(path)


def remove_default_apps(path):
    """sed -i -E '/^[^=]+=(Dorico|...)\\.desktop;?$/d' PATH"""
    with open(path, "rb") as f:
        lines = f.read().decode("utf-8", "surrogateescape").splitlines(keepends=True)
    kept = [l for l in lines if not DEFAULT_APP.match(l.rstrip("\n"))]
    with open(path, "wb") as f:
        f.write("".join(kept).encode("utf-8", "surrogateescape"))


def remove_desktop_shortcuts():
    """Windows shortcuts Steinberg's installers put on the desktop, and launchers Wine's menu builder created
    there for programs in Torquio's prefix."""
    desktop = folders.desktop_dir()
    prefix = paths.prefix_dir()
    dirs = [desktop, os.path.join(prefix, "drive_c/users/Public/Desktop")]
    dirs += glob.glob(os.path.join(glob.escape(prefix), "drive_c/users/*/Desktop"))
    for directory in dirs:
        if not os.path.isdir(directory):
            continue
        try:
            entries = list(os.scandir(directory))
        except OSError:
            continue
        for entry in entries:
            if entry.is_file(follow_symlinks=False) and any(fnmatch.fnmatchcase(entry.name, p) for p in WINDOWS_SHORTCUTS):
                _rm(entry.path)
    needles = torquio_dir_patterns()
    for launcher in glob.glob(os.path.join(glob.escape(desktop), "*.desktop")):
        if os.path.isfile(launcher) and _mentions(launcher, needles):
            _rm(launcher)


def container_images(mgr):
    """The downloaded prebuilt engines and the container snapshots Torquio made, as `mgr` lists them."""
    name, repo = paths.container_name(), paths.image_repo()
    out = run.capture([mgr, "images", "--format", "{{.Repository}}:{{.Tag}}"])[1]
    return [image for image in out.split()
            if re.match(f"^localhost/{name}:gpu-", image) or re.match(f"^{repo}:", image)]
