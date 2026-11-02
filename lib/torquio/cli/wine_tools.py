"""Wine Tools & Maintenance (main menu)."""
import os
import subprocess

from .. import config, paths, prefix, run, ui
from ..ui import BLUE, RESET, WINE, echo
from . import engine as engine_cli, tools

OPTIONS = [
    "Run Wine Configuration (winecfg)",
    "Run Registry Editor (regedit)",
    "Run Control Panel (control)",
    "Run File Manager (explorer)",
    "Run Command Prompt (cmd)",
    "Reboot Wine Prefix (wineboot -r)",
    "Shutdown Wine Server (wineserver -k)",
    "Monitor XWayland Keyboard Events (xev)",
    "Run Custom Installer/Executable (.exe/.msi)",
    "Open C: Drive in Host File Manager",
    "Enable Kernel Fast Sync (NTsync)",
    "Update / Rebuild Wine Engine",
    "GPU for AI Plug-ins (e.g. Cantai)",
    "[Back to main menu]",
]
PROGRAMS = {"1": "winecfg", "2": "regedit", "3": "wine control", "4": "wine explorer", "5": "wine cmd"}


def run_program(program, freetype):
    """A Wine program in the prefix, on the terminal."""
    prefix.enter_visibly(prefix.env_script(freetype) + program)


def reboot_prefix(freetype):
    print("Rebooting Wine prefix...")
    run_program("wineboot -r", freetype)
    print("Prefix reboot completed.")


def shutdown_wine():
    print("Shutting down Wine server...")
    prefix.enter_visibly(prefix.env_script() + "wineserver -k && wineserver -w")
    print("Wine server shutdown complete.")


def xev():
    """Returns False when the user declined installing xev (the menu then shows again without a pause)."""
    name = paths.container_name()
    if run.interactive(["distrobox", "enter", name, "--", "command", "-v", "xev"],
                       stdout=run.DEVNULL, stderr=run.DEVNULL) != 0:
        print("xev (X11 Event Viewer) is not installed in the container.")
        if ui.no(ui.ask("Would you like to install it now? [Y/n]: ")):
            return False
        print("Installing x11-utils...")
        run.check(run.interactive(["distrobox", "enter", name, "--", "sudo", "apt", "update"]), True)
        run.check(run.interactive(["distrobox", "enter", name, "--", "sudo", "apt", "install", "-y", "x11-utils"]), True)
    print("Launching X11 Event Viewer (xev)...")
    print("Focus the small white window that appears and press keys to monitor events.")
    print("Press Ctrl+C inside this terminal to exit the monitor.")
    run.interactive(["distrobox", "enter", name, "--", "xev", "-event", "keyboard"])
    return True


def manage():
    while True:
        echo(f"{BLUE}=== Wine Tools & Maintenance ==={RESET}")
        echo()
        for i, label in enumerate(OPTIONS, 1):
            echo(f"  {WINE}{i}){RESET} {label}")
        echo()
        choice = ui.ask("Select an option (1-14): ")
        freetype = config.get_text("freetype_interpreter", "40")
        prompt = True
        if choice in PROGRAMS:
            run_program(PROGRAMS[choice], freetype)
        elif choice == "6":
            reboot_prefix(freetype)
        elif choice == "7":
            shutdown_wine()
        elif choice == "8":
            if not xev():
                ui.clear()
                continue
        elif choice == "9":
            tools.run_custom_exe()
        elif choice == "10":
            drive_c = os.path.join(paths.prefix_dir(), "drive_c")
            if os.path.isdir(drive_c):
                print("Opening C: Drive in host file manager...")
                try:
                    subprocess.Popen(["xdg-open", drive_c], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
                except OSError:
                    pass
                prompt = False
            else:
                print("Error: Wine prefix C: drive does not exist yet.")
        elif choice == "11":
            run.check(tools.enable_ntsync(), True)
        elif choice == "12":
            run.check(engine_cli.update_wine_engine(), True)
        elif choice == "13":
            run.check(engine_cli.manage_ai_gpu(), True)
            prompt = False
        else:
            return
        if prompt:
            echo()
            ui.pause()
        ui.clear()
