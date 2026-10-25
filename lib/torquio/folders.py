"""Host folders mapped into the Wine prefix: as drive letters (dosdevices) or as shortcuts on the Desktop."""
import glob
import locale
import os
import re

from . import paths, run

DRIVE_LETTERS = "defghijklmnopqrstuvwxy"  # letters checked for existing mappings
FREE_LETTERS = DRIVE_LETTERS + "z"         # letters a new mapping may take


def dosdevices():
    return os.path.join(paths.prefix_dir(), "dosdevices")


def resolve(path):
    """readlink -f"""
    return os.path.realpath(path)


def realpath_command(path):
    """`realpath PATH` (its error message shows on the terminal, as it did in Bash); "" if it fails."""
    return run.capture(["realpath", path], stderr=None)[1].rstrip("\n")


def mapped_drives():
    """[(letter, target)] for the drive letters that are links."""
    drives = []
    for letter in DRIVE_LETTERS:
        link = os.path.join(dosdevices(), f"{letter}:")
        if os.path.islink(link):
            drives.append((letter, resolve(link)))
    return drives


def drive_for(folder):
    """The drive letter (upper case, with colon) a folder is mapped to, or ""."""
    for letter, target in mapped_drives():
        if target == folder:
            return f"{letter.upper()}:"
    return ""


def free_drive():
    """The first unused drive letter ("x:"), or ""."""
    for letter in FREE_LETTERS:
        if not os.path.lexists(os.path.join(dosdevices(), f"{letter}:")):
            return f"{letter}:"
    return ""


def map_drive(folder, drive_letter):
    link = os.path.join(dosdevices(), drive_letter)
    if os.path.lexists(link) or os.path.islink(link):
        os.remove(link)
    os.symlink(folder, link)


def unmap_drive(letter):
    try:
        os.remove(os.path.join(dosdevices(), f"{letter}:"))
    except FileNotFoundError:
        pass


def desktop_dir():
    """The Desktop folder: $XDG_DESKTOP_DIR, as ~/.config/user-dirs.dirs sets it if that exists, else ~/Desktop."""
    home = paths.home()
    value = os.environ.get("XDG_DESKTOP_DIR", "")
    try:
        with open(os.path.join(home, ".config/user-dirs.dirs")) as f:
            for line in f:
                m = re.match(r'\s*XDG_DESKTOP_DIR=(.*)$', line.rstrip("\n"))
                if m:
                    value = m.group(1).strip()
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                        value = value[1:-1]
                    value = value.replace("${HOME}", home).replace("$HOME", home)
    except OSError:
        pass
    return value or os.path.join(home, "Desktop")


def locale_sorted(names):
    """In the order a Bash glob lists them (the locale's collation)."""
    try:
        locale.setlocale(locale.LC_COLLATE, "")
    except locale.Error:
        pass
    return sorted(names, key=locale.strxfrm)


def desktop_shortcuts():
    """[(path, target)] for the links on the Desktop that point to folders."""
    shortcuts = []
    directory = desktop_dir()
    if os.path.isdir(directory):
        for path in locale_sorted(glob.glob(os.path.join(glob.escape(directory), "*"))):
            if os.path.islink(path):
                target = resolve(path)
                if os.path.isdir(target):
                    shortcuts.append((path, target))
    return shortcuts


def remove_link(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def replace_link(target, link):
    """rm -f LINK; ln -sf TARGET LINK"""
    if os.path.islink(link) or (os.path.lexists(link) and not os.path.isdir(link)):
        os.remove(link)
    os.symlink(target, link)
