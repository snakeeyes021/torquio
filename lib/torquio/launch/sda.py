"""torquio-sda-handler: start the Steinberg Download Assistant, optionally with a sign-in link
(net-steinberg-sda://). Without one, a background watcher refreshes Torquio's icons once Dorico is installed."""
import fnmatch
import os
import re
import time

from .. import config, paths, run, uninstall
from . import common

SDA_RUNNING = re.compile(r"Steinberg Download Assistant\.exe|STEI~B2R\.EXE|aria2c\.exe", re.I)


def sda_running():
    out = run.capture(["distrobox", "enter", paths.container_name(), "--", "bash", "-c", "ps auxww"], stdin=None,
                      stderr=None)[1]
    return any(SDA_RUNNING.search(line) for line in out.splitlines())


def temp_files(pattern):
    """find drive_c/users -path "*/AppData/Local/Temp/*" -name PATTERN"""
    found = []
    for root, dirs, files in os.walk(os.path.join(paths.prefix_dir(), "drive_c/users")):
        for name in dirs + files:
            path = os.path.join(root, name)
            if fnmatch.fnmatchcase(path, "*/AppData/Local/Temp/*") and fnmatch.fnmatchcase(name, pattern):
                found.append(path)
    return found


def dorico_installed(status_file):
    """Whether the Download Assistant's status file reports a successful Dorico installation."""
    try:
        with open(status_file, errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return False
    artifact = success = ""
    for line in lines:
        m = re.search(r'"artifactId":\s*"[^"]*"', line)
        if m and not artifact:
            artifact = (m.group(0).split('"') + ["", "", "", ""])[3]
        m = re.search(r'"success":\s*(true|false)', line)
        if m and not success:
            success = "".join(m.group(0).split(":", 1)[1].split())
    return bool(re.search("Dorico.*Application_Installer", artifact)) and success == "true"


def refresh_icons():
    run.check(run.interactive(["distrobox", "enter", paths.container_name(), "--", "bash", "-c",
                               f'cd "{paths.repo_dir()}" && ./scripts/2-install/extract_icons.sh']), True)
    home = paths.home()
    run.interactive(["update-desktop-database", os.path.join(home, ".local/share/applications/")],
                    stdout=run.DEVNULL, stderr=run.DEVNULL)
    if run.have("gtk-update-icon-cache"):
        run.interactive(["gtk-update-icon-cache", "-f", "-t", os.path.join(home, ".local/share/icons/hicolor/")],
                        stdout=run.DEVNULL, stderr=run.DEVNULL)
    # Touch directories to signal GNOME Shell to reload applications and icons
    for directory in (".local/share/icons/hicolor", ".local/share/applications"):
        try:
            os.utime(os.path.join(home, directory))
        except OSError:
            pass


def watch():
    """Until the Download Assistant exits: remove the Windows shortcuts installers put on the desktop, and
    refresh the icons once Dorico's installation succeeds. Writes ~/.local/share/torquio/sda_watcher.log."""
    print("Starting background watcher for Dorico installation and shortcut cleanup...")
    # Clean up old status files to avoid stale matches
    for path in temp_files("*.json"):
        try:
            os.remove(path)
        except OSError:
            pass
    print("Waiting for SDA processes to start...")
    for _ in range(15):
        if sda_running():
            print("SDA processes detected active.")
            break
        time.sleep(2)
    else:
        print("SDA processes never started. Exiting watcher.")
        return
    while True:
        uninstall.remove_windows_shortcuts()
        status = temp_files("*Dorico*Application*Installer.json")
        if status and os.path.isfile(status[0]) and dorico_installed(status[0]):
            print("Dorico installation success detected! Extracting icons...")
            refresh_icons()
            try:
                os.rename(status[0], status[0] + ".processed")
            except OSError:
                try:
                    os.remove(status[0])
                except OSError:
                    pass
        if not sda_running():
            print("SDA processes terminated. Exiting watcher.")
            break
        time.sleep(4)


def start_watcher():
    if os.fork() != 0:
        return
    try:
        log = os.open(os.path.join(paths.home(), ".local/share/torquio/sda_watcher.log"),
                      os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o666)
        os.dup2(log, 1)
        os.dup2(log, 2)
        os.close(log)
        import sys
        sys.stdout.reconfigure(line_buffering=True)
        watch()
    except SystemExit:
        pass
    finally:
        os._exit(0)


def launch(url=""):
    if not url:
        try:
            common.manage_graphics(restartable=True)
        except common.Declined:
            return 1
    common.fix_key_repeat()
    os.makedirs(os.path.join(paths.home(), ".local/share/torquio"), exist_ok=True)
    if not url:
        start_watcher()
    runner = common.write_runner("run-sda.sh", common.runner_text("run-sda.sh.in", {
        "TORQUIO_PREFIX_DIR": paths.prefix_dir(),
        "WINE_CUSTOM_BIN": paths.WINE_CUSTOM_BIN,
        "FREETYPE_INTERP": config.get_text("freetype_interpreter", "40"),
    }))
    common.handover("sda_url.txt", url)
    # Sweep before launching to catch any leftovers
    uninstall.remove_windows_shortcuts()
    run.check(common.run_in_container(runner), True)
    common.report_crashes()
    # Sweep after exiting to catch any shortcuts written right at the end
    uninstall.remove_windows_shortcuts()
    return 0
