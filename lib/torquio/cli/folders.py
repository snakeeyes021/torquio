"""Manage Folder Mappings (main menu, `torquio --map_folder`)."""
import os

from .. import folders, run, ui
from ..ui import BLUE, GRAY, RESET, WINE, YELLOW, echo


def pick_folder(strict):
    """A folder from the desktop's folder picker, or typed in without one."""
    if run.have("zenity"):
        return run.capture(["zenity", "--file-selection", "--directory", "--title=Select Folder to Map"])[1].rstrip("\n")
    if run.have("kdialog"):
        return run.capture(["kdialog", "--getexistingdirectory", "--title=Select Folder to Map"])[1].rstrip("\n")
    return ui.ask("Enter the absolute path of the local folder: ", strict)


def map_folder(host_folder="", map_type="", drive_letter="", strict=True):
    """map_folder: returns 0 when a mapping exists afterwards, 1 when cancelled or failed. `strict`: the
    caller is in set -e context (end of input at a prompt stops Torquio)."""
    if not host_folder:
        echo("=== Map Local Folder ===")
        host_folder = pick_folder(strict)
        if not host_folder or not os.path.isdir(host_folder):
            echo("Error: Invalid folder path. Mapping cancelled.")
            return 1

    real = folders.realpath_command(host_folder)
    if not os.path.isdir(real):
        print(f"Error: Local folder '{real}' does not exist.")
        return 1
    echo()
    echo(f"Selected local folder: {WINE}{real}{RESET}")
    echo()

    if not os.path.isdir(folders.dosdevices()):
        echo("Error: Wine prefix has not been initialized. Please run setup first.")
        return 1

    if not map_type:
        echo("Select how you would like to map this folder in Wine:")
        echo(f"  {WINE}1){RESET} As a Mapped Network Drive (e.g., D:\\\\, E:\\\\)")
        echo(f"  {WINE}2){RESET} As a Shortcut inside your Desktop folder (auto-expanded in file pickers)")
        echo(f"  {WINE}3){RESET} [Cancel]")
        echo()
        choice = ui.ask("Select choice (1-3): ", strict)
        if choice == "1":
            map_type = "drive"
        elif choice == "2":
            map_type = "desktop"
        else:
            echo("Mapping cancelled.")
            return 1

    if map_type == "drive":
        existing = folders.drive_for(real)
        if existing:
            # As in Bash, where "...$existing_drive\\${reset}" left echo -e a "\\\\033[0m": a literal "033[0m"
            echo(f"{YELLOW}Warning: Folder '{real}' is already mapped to network drive {existing}\\\\033[0m")
            if not ui.yes(ui.ask("Are you sure you want to map it again to a different drive letter? [y/N]: ", strict)):
                echo("Mapping cancelled.")
                return 1
        if not drive_letter:
            drive_letter = folders.free_drive()
            if not drive_letter:
                echo("Error: No available drive letters left!")
                return 1
        drive_letter = drive_letter.lower()
        if not drive_letter.endswith(":"):
            drive_letter += ":"
        link = os.path.join(folders.dosdevices(), drive_letter)
        if os.path.islink(link) and folders.resolve(link) == real:
            print(f"Folder '{real}' is already mapped to Wine drive {drive_letter.upper()}\\")
            return 0
        folders.map_drive(real, drive_letter)
        print(f"Successfully mapped '{real}' to Wine drive {drive_letter.upper()}\\")
        echo(f"{GRAY}Note: The drive letter will appear in Wine file dialogs once all Wine applications{RESET}")
        echo(f"{GRAY}      are closed (or after you run a Wine server shutdown in the Maintenance menu).{RESET}")
        return 0

    if map_type == "desktop":
        desktop = folders.desktop_dir()
        os.makedirs(desktop, exist_ok=True)
        name = os.path.basename(real)
        dest = os.path.join(desktop, name)
        if os.path.islink(dest) and folders.resolve(dest) == real:
            print(f"Folder '{real}' is already mapped to Desktop shortcut: {dest}")
            return 0
        if os.path.lexists(dest) and not os.path.islink(dest):
            print(f"Error: A physical file or folder named '{name}' already exists on your Desktop.")
            custom = ui.ask("Enter a custom shortcut name: ", strict)
            if not custom:
                print("Mapping cancelled.")
                return 1
            dest = os.path.join(desktop, custom)
        if os.path.islink(dest) or (os.path.lexists(dest) and not os.path.isdir(dest)):
            os.remove(dest)
        os.symlink(real, dest)
        print(f"Successfully mapped '{real}' to Desktop shortcut: {os.path.basename(dest)}")
        return 0
    return 0


def unmap_folder(strict=True):
    echo("=== Unmap Local Folder ===")
    entries = []  # (label, kind, value)
    if os.path.isdir(folders.dosdevices()):
        for letter, target in folders.mapped_drives():
            entries.append((f"[Network Drive]    {letter.upper()}: -> {target}", "drive", letter))
    for path, target in folders.desktop_shortcuts():
        entries.append((f"[Desktop Shortcut] {os.path.basename(path)} -> {target}", "desktop", path))
    if not entries:
        echo("No mapped folders found.")
        return 1
    echo("Currently mapped folders:")
    for i, (label, _, _) in enumerate(entries, 1):
        print(f"  {i}) {label}")
    print(f"  {len(entries) + 1}) [Cancel]")
    echo()
    choice = ui.ask(f"Select a shortcut to unmap (1-{len(entries) + 1}): ", strict)
    if choice.isascii() and choice.isdigit() and 1 <= int(choice) <= len(entries):
        _, kind, value = entries[int(choice) - 1]
        if kind == "drive":
            folders.unmap_drive(value)
            echo(f"Successfully unmapped drive {value.upper()}:")
            echo(f"{GRAY}Note: The drive letter will disappear from Wine file dialogs once all Wine applications{RESET}")
            echo(f"{GRAY}      are closed (or after you run a Wine server shutdown in the Maintenance menu).{RESET}")
        else:
            folders.remove_link(value)
            print(f"Successfully removed Desktop shortcut: {os.path.basename(value)}")
        return 0
    echo("Operation cancelled.")
    return 1


def manage():
    while True:
        echo(f"{BLUE}=== Manage Folder Mappings ==={RESET}")
        echo()
        echo(f"  {WINE}1){RESET} Map a Local Folder to Wine")
        echo(f"  {WINE}2){RESET} Unmap an Existing Wine Folder")
        echo(f"  {WINE}3){RESET} [Back to main menu]")
        echo()
        choice = ui.ask("Select an option (1-3): ")
        if choice in ("1", "2"):
            echo()
            # Called as `if map_folder; then` in Bash: set -e doesn't apply inside
            if (map_folder(strict=False) if choice == "1" else unmap_folder(strict=False)) == 0:
                echo()
                ui.pause()
        else:
            return
        ui.clear()

