"""Single tools: run a custom installer, enable ntsync, export logs, the Settings menu and the update check."""
import os
import platform
import time

from .. import config, paths, prefix, run, ui
from ..ui import BLUE, GRAY, GREEN, RED, RESET, WINE, YELLOW, echo


def run_custom_exe(selected=""):
    print("=== Run Custom Installer or Executable ===")
    print()
    if not selected:
        if run.have("zenity"):
            selected = run.capture(["zenity", "--file-selection", "--file-filter=Executables (*.exe *.msi) | *.exe *.msi",
                                    "--title=Select Executable to Run"])[1].rstrip("\n")
        elif run.have("kdialog"):
            selected = run.capture(["kdialog", "--getopenfilename", paths.home(), "*.exe *.msi",
                                    "--title=Select Executable to Run"])[1].rstrip("\n")
        else:
            selected = ui.ask("Enter the absolute path to the .exe or .msi file: ")
    if not selected or not os.path.isfile(selected):
        print("No valid file selected. Operation cancelled.")
        return
    print(f"Running: {selected}")
    windows = prefix.windows_path(selected)
    freetype = config.get_text("freetype_interpreter", "40")
    program = f'msiexec /i "{windows}"' if selected.endswith(".msi") else f'"{windows}"'
    prefix.enter_visibly(prefix.env_script(freetype) + f"wine {program}")
    print("Execution completed.")


def ntsync_active():
    try:
        import stat
        host_char = stat.S_ISCHR(os.stat("/run/host/dev/ntsync").st_mode)
    except OSError:
        host_char = False
    return os.path.exists("/dev/ntsync") or host_char


def enable_ntsync():
    """enable_ntsync; returns its exit status."""
    echo()
    if ntsync_active():
        echo(f"{GREEN}Kernel Fast Sync (NTsync) is already active on this system (/dev/ntsync).{RESET}")
        return 0
    if not run.succeeds(["modinfo", "ntsync"]):
        echo(f"{YELLOW}The ntsync kernel module was not found for running kernel {platform.release()}.{RESET}")
        echo("A Linux kernel version 6.14 or newer with CONFIG_NTSYNC enabled is required.")
        return 1
    echo(f"{BLUE}=== Enable Kernel Fast Sync (NTsync) ==={RESET}")
    echo()
    echo("NTsync is supported by your kernel and can significantly speed up some UI operations in Dorico.")
    answer = ui.ask("Would you like to activate and persist it across reboots? (We ask because it requires sudo) [Y/n]: ")
    if not answer or ui.yes(answer):
        echo("Activating NTsync module...")
        if run.interactive(["sudo", "modprobe", "ntsync"]) == 0 and \
                run.interactive(["sudo", "tee", "/etc/modules-load.d/ntsync.conf"], input=b"ntsync\n",
                                stdout=run.DEVNULL) == 0:
            echo(f"{GREEN}NTsync successfully activated and persisted across reboots.{RESET}")
            return 0
        echo(f"{RED}Failed to activate NTsync.{RESET}")
        return 1
    echo(f"{GRAY}Operation cancelled.{RESET}")
    return 0


def export_logs():
    from .. import logs
    print("=== Export Logs ===")
    print("Collecting logs...")
    try:
        zip_file = logs.write_zip()
    except Exception:
        import traceback
        traceback.print_exc()  # what the separate export process showed before
        print("Error: the logs could not be exported.")
        return
    print()
    print(f"Saved: {zip_file}")
    print()
    print("Find the exported log file at the above path. Your email address, username, computer name and license "
          "details have been removed.")
    print()
    echo(f"{YELLOW}Project names are still in it, so have a quick look before posting it publicly. GitHub issues and "
         f"forum posts are usually permanent; if you can, consider sending it by email instead.{RESET}")


def check_for_updates():
    """Fetch from GitHub at most once a day (quietly; failures don't matter), so pending_updates() can tell."""
    if config.get_text("check_for_updates", "true") != "true":
        return
    repo = paths.repo_dir()
    if not run.succeeds(["git", "-C", repo, "rev-parse", "--abbrev-ref", "@{u}"]):
        return
    stamp = os.path.join(paths.cache_dir(), "last-update-check")
    now = int(time.time())
    try:
        with open(stamp) as f:
            last = int(f.read().strip() or 0)
    except (OSError, ValueError):
        last = 0
    if now - last < 86400:
        return
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=5")
    if run.succeeds(["timeout", "8", "git", "-C", repo, "fetch", "--quiet"], env=env):
        os.makedirs(paths.cache_dir(), exist_ok=True)
        with open(stamp, "w") as f:
            f.write(f"{now}\n")


def pending_updates():
    """Commits the last check found on GitHub (no network access)."""
    if config.get_text("check_for_updates", "true") != "true":
        return "0"
    code, out = run.capture(["git", "-C", paths.repo_dir(), "rev-list", "--count", "HEAD..@{u}"])
    return out.strip() if code == 0 else "0"


def manage_settings():
    while True:
        auto = "On" if config.get_text("check_for_updates", "true") == "true" else "Off"
        echo()
        echo(f"{BLUE}=== Settings ==={RESET}")
        echo()
        echo(f"  {WINE}1){RESET} Automatically check for updates: {WINE}{auto}{RESET}")
        echo(f"  {WINE}2){RESET} [Back]")
        echo()
        if ui.ask("Select an option (1-2): ", strict=False) != "1":
            return
        if auto == "On":
            config.set_text("check_for_updates", "false")
            print("Torquio won't check for updates on its own any more (Update Torquio still works).")
        else:
            config.set_text("check_for_updates", "true")
            print("Torquio will check GitHub for updates once a day when you open it.")
