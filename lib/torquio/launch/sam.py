"""torquio-sam: start the Steinberg Activation Manager, optionally with a sign-in link
(net-steinberg-sam://, the web login's way back)."""
import os

from .. import config, paths, run
from ..cli.header import clock_offset_ok
from . import common

CLOCK_MESSAGE = ("WARNING: Your system clock is out of sync!\\n\\nThis is highly likely to cause Steinberg Activation "
                 "Manager (SAM) licensing errors and deactivations.\\n\\nPlease synchronize your system clock to "
                 "prevent licensing issues.")
TERMINALS = [("xdg-terminal-exec", ["--"]), ("gnome-terminal", ["--"]), ("ptyxis", ["--"]), ("tilix", ["-e"]),
             ("konsole", ["-e"]), ("xfce4-terminal", ["-e"]), ("alacritty", ["-e"]), ("kitty", []), ("xterm", ["-e"])]


def warn_about_clock():
    """In the background: if the system clock is off (the Activation Manager fails then), say so in a dialog,
    or open Torquio in a terminal (its header explains) where there's no dialog tool for the desktop."""
    if os.fork() != 0:
        return
    try:
        desynced = os.environ.get("TORQUIO_TEST_CLOCK_DESYNC") == "true" or not clock_offset_ok()
        if desynced:
            desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
            if os.environ.get("TORQUIO_FORCE_TERMINAL") == "true":
                desktop = "other"
            if any(d in desktop for d in ("gnome", "kde", "unity", "plasma")):
                if ("kde" in desktop or "plasma" in desktop) and run.have("kdialog"):
                    run.spawn(["kdialog", "--warningcontinuecancel", CLOCK_MESSAGE, "--title=Torquio Time Sync Warning"])
                elif run.have("zenity"):
                    run.spawn(["zenity", "--warning", f"--text={CLOCK_MESSAGE}", "--title=Torquio Time Sync Warning",
                               "--width=400"])
            else:
                torquio = os.path.join(paths.home(), ".local/bin/torquio")
                for terminal, flag in TERMINALS:
                    if run.have(terminal):
                        run.interactive([terminal, *flag, torquio])
                        break
    finally:
        os._exit(0)


def launch(url=""):
    warn_about_clock()
    try:
        common.manage_graphics(restartable=not url)
    except common.Declined:
        return 1
    common.fix_key_repeat()
    runner = common.write_runner("run-sam.sh", common.runner_text("run-sam.sh.in", {
        "TORQUIO_PREFIX_DIR": paths.prefix_dir(),
        "WINE_CUSTOM_BIN": paths.WINE_CUSTOM_BIN,
        "FREETYPE_INTERP": config.get_text("freetype_interpreter", "40"),
    }))
    common.handover("sam_url.txt", url)
    run.check(common.run_in_container(runner), True)
    common.report_crashes()
    return 0
