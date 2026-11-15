"""torquio-dorico: start Dorico, optionally opening a project (the .dorico file association)."""
from .. import config, dialogs, paths, plugins
from . import common

MISSING = ("Dorico could not be located in your Wine prefix.\n\nPlease open the Steinberg Download Assistant (SDA) "
           "to download and install Dorico.")


def launch(file_to_open=""):
    try:
        common.manage_graphics(restartable=not file_to_open)
    except common.Declined:
        return 1
    common.fix_key_repeat()
    # A plug-in installed outside Torquio's installer (e.g. Cantai with Run Custom Installer) gets what it
    # needs before Dorico loads it; otherwise Cantai's editor stays blank (no WebView2)
    if plugins.missing():
        dialogs.notify("Torquio", "Setting up what Cantai needs before Dorico starts (a one-time download); "
                       "Dorico opens when it's done.")
        plugins.provision()
    runner = common.write_runner("run-dorico.sh", common.runner_text("run-dorico.sh.in", {
        "TORQUIO_PREFIX_DIR": paths.prefix_dir(),
        "WINE_CUSTOM_BIN": paths.WINE_CUSTOM_BIN,
        "FREETYPE_INTERP": config.get_text("freetype_interpreter", "40"),
        # GPU for AI plug-ins (Cantai): "auto" (strongest GPU), "off" (CPU only) or (part of) a GPU's name
        "AI_GPU": config.get_text("ai_gpu", "auto"),
        "TORQUIO_DATA_DIR": paths.data_dir(),
        "TORQUIO_REPO_DIR": paths.repo_dir(),
    }))
    common.handover("launch_path.txt", file_to_open)
    common.run_program(runner, MISSING)
    common.report_crashes()
    return 0
