"""torquio-dorico: start Dorico, optionally opening a project (the .dorico file association)."""
from .. import config, paths, run
from . import common


def launch(file_to_open=""):
    try:
        common.manage_graphics(restartable=not file_to_open)
    except common.Declined:
        return 1
    common.fix_key_repeat()
    runner = common.write_runner("run-dorico.sh", common.runner_text("run-dorico.sh.in", {
        "TORQUIO_PREFIX_DIR": paths.prefix_dir(),
        "WINE_CUSTOM_BIN": paths.WINE_CUSTOM_BIN,
        "FREETYPE_INTERP": config.get_text("freetype_interpreter", "40"),
        # GPU for AI plug-ins (Cantai): "auto" (strongest GPU), "off" (CPU only) or (part of) a GPU's name
        "AI_GPU": config.get_text("ai_gpu", "auto"),
        "TORQUIO_DATA_DIR": paths.data_dir(),
    }))
    common.handover("launch_path.txt", file_to_open)
    run.check(common.run_in_container(runner), True)
    common.report_crashes()
    return 0
