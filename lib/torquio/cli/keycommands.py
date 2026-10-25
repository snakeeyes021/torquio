"""Manage Dorico Key Commands (main menu, `torquio --export_key_commands` / `--import_key_commands`)."""
import fnmatch
import glob
import os
import shutil
import zipfile

from .. import paths, run, ui
from ..ui import BLUE, RESET, WINE, echo

BACKUP_NAME = "torquio_keycommands_backup.zip"


def walk(top):
    """(path, is_dir) below `top`, in the order `find` lists them (directory order, depth first)."""
    try:
        entries = list(os.scandir(top))
    except OSError:
        return
    for entry in entries:
        is_dir = entry.is_dir(follow_symlinks=False)
        yield entry.path, is_dir
        if is_dir:
            yield from walk(entry.path)


def dorico_appdata():
    """`find drive_c/users -type d -path "*/AppData/Roaming/Steinberg/Dorico*" | head -n 1`"""
    for path, is_dir in walk(os.path.join(paths.prefix_dir(), "drive_c/users")):
        if is_dir and fnmatch.fnmatchcase(path, "*/AppData/Roaming/Steinberg/Dorico*"):
            return path
    return ""


def downloads_dir():
    return os.environ.get("XDG_DOWNLOAD_DIR") or os.path.join(paths.home(), "Downloads")


def export():
    echo("=== Exporting Key Commands Backup ===")
    folder = dorico_appdata()
    if not folder or not os.path.isdir(folder):
        echo("Error: Dorico AppData directory not found. Please make sure Dorico has been installed and run.")
        return
    files = [p for p, is_dir in walk(folder)
             if not is_dir and os.path.isfile(p) and not os.path.islink(p)
             and fnmatch.fnmatchcase(os.path.basename(p), "keycommands_*.json")]
    if not files:
        echo("No keycommands_*.json files found to export.")
        return
    echo("Found files to export:")
    for f in files:
        print(f"  - {os.path.basename(f)}")
    downloads = downloads_dir()
    os.makedirs(downloads, exist_ok=True)
    zip_file = os.path.join(downloads, BACKUP_NAME)
    # Only the files directly in Dorico's folder go in (the list above searched its subfolders too)
    with zipfile.ZipFile(zip_file, "w") as z:
        for f in glob.glob(os.path.join(glob.escape(folder), "keycommands_*.json")):
            z.write(f, os.path.basename(f))
    print(f"Successfully compressed and exported key commands to: {zip_file}")


def pick_backup(downloads):
    if run.have("zenity"):
        return run.capture(["zenity", "--file-selection", "--file-filter=Backup (*.zip *.json) | *.zip *.json",
                            "--title=Select Key Commands Backup File"])[1].rstrip("\n")
    if run.have("kdialog"):
        return run.capture(["kdialog", "--getopenfilename", downloads, "*.zip *.json",
                            "--title=Select Key Commands Backup File"])[1].rstrip("\n")
    return ui.ask("Enter path to key commands backup file (.zip or .json): ")


def import_():
    echo("=== Importing Key Commands Backup ===")
    downloads = downloads_dir()
    try:
        backups = [e.path for e in os.scandir(downloads)
                   if e.is_file(follow_symlinks=False)
                   and (e.name == BACKUP_NAME or fnmatch.fnmatchcase(e.name, "keycommands_*.json"))]
    except OSError:
        backups = []
    selected = ""
    if len(backups) == 1:
        selected = backups[0]
        print(f"Auto-detected backup file: {os.path.basename(selected)}")
    elif len(backups) > 1:
        print(f"Multiple backup files found in {downloads}:")
        for i, b in enumerate(backups, 1):
            print(f"  {i}) {os.path.basename(b)}")
        print(f"  {len(backups) + 1}) [Browse...]")
        choice = ui.ask(f"Select a file to import (1-{len(backups) + 1}): ")
        if choice.isascii() and choice.isdigit() and 1 <= int(choice) <= len(backups):
            selected = backups[int(choice) - 1]
    if not selected:
        selected = pick_backup(downloads)
    if not selected or not os.path.isfile(selected):
        echo("No backup file selected. Import cancelled.")
        return
    print(f"Staging backup: {selected}")
    staged = os.path.join(paths.data_dir(), "staged_keycommands")
    shutil.rmtree(staged, ignore_errors=True)
    for leftover in glob.glob(os.path.join(glob.escape(paths.data_dir()), "staged_keycommands.*")):
        if not os.path.isdir(leftover) or os.path.islink(leftover):
            os.remove(leftover)
    os.makedirs(staged, exist_ok=True)
    if selected.endswith(".zip"):
        run.succeeds(["unzip", "-o", selected, "-d", staged + "/"])
    else:
        shutil.copy(selected, staged + "/")
    echo("Keyboard shortcuts staged successfully! They will be automatically imported the next time you launch Dorico.")


def manage():
    while True:
        echo(f"{BLUE}=== Manage Dorico Key Commands ==={RESET}")
        echo()
        echo(f"  {WINE}1){RESET} Export Key Commands (Backup to Zip)")
        echo(f"  {WINE}2){RESET} Import Key Commands (Restore from Backup)")
        echo(f"  {WINE}3){RESET} [Back to main menu]")
        echo()
        choice = ui.ask("Select an option (1-3): ")
        if choice == "1":
            export()
        elif choice == "2":
            import_()
        else:
            return
        echo()
        ui.pause()
