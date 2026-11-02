"""torquio-sam: start the Steinberg Activation Manager, optionally with a sign-in link
(net-steinberg-sam://, the web login's way back)."""
import os
import threading

from .. import config, dialogs, paths, run
from ..cli.header import clock_offset_ok
from . import common

CLOCK_TITLE = "Torquio Time Sync Warning"
CLOCK_MESSAGE = ("WARNING: Your system clock is out of sync!\n\nThis is highly likely to cause Steinberg Activation "
                 "Manager (SAM) licensing errors and deactivations.\n\nPlease synchronize your system clock to "
                 "prevent licensing issues.")
MISSING = ("Steinberg Activation Manager could not be located in your Wine prefix.\n\nPlease open the Steinberg "
           "Download Assistant (SDA) to install it.")
TERMINALS = [("xdg-terminal-exec", ["--"]), ("gnome-terminal", ["--"]), ("ptyxis", ["--"]), ("tilix", ["-e"]),
             ("konsole", ["-e"]), ("xfce4-terminal", ["-e"]), ("alacritty", ["-e"]), ("kitty", []), ("xterm", ["-e"])]


def start_clock_check():
    """Check the system clock (a web request, up to 3 seconds) while the launcher gets everything else ready."""
    result = {}

    def check():
        result["ok"] = os.environ.get("TORQUIO_TEST_CLOCK_DESYNC") != "true" and clock_offset_ok()

    thread = threading.Thread(target=check, daemon=True)
    thread.start()
    return thread, result


def warn_about_clock(clock_check):
    """If the system clock is off (the Activation Manager fails then), say so before the Activation Manager
    starts (shown alongside it, the warning ended up behind its window), and wait until it's closed. Where no
    dialog or notification can be shown, open Torquio in a terminal instead (its header explains)."""
    thread, result = clock_check
    thread.join(5)
    if result.get("ok", True):
        return
    if os.environ.get("TORQUIO_FORCE_TERMINAL") != "true" and dialogs.message("warning", CLOCK_MESSAGE, CLOCK_TITLE):
        return
    torquio = os.path.join(paths.home(), ".local/bin/torquio")
    for terminal, flag in TERMINALS:
        if run.have(terminal):
            run.spawn([terminal, *flag, torquio])
            break


def launch(url=""):
    clock_check = start_clock_check()
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
    warn_about_clock(clock_check)
    common.run_program(runner, MISSING)
    common.report_crashes()
    return 0
