"""Internal commands the Bash scripts call while the port is under way (not for users; see docs/REFACTOR.md).

Bash runs these through torquio_py in scripts/common.sh (`torquio_py config-get KEY DEFAULT`). For
development, `PYTHONPATH=lib python3 -m torquio COMMAND ...` does the same.
"""
import sys

# Each command imports only what it needs: get_config_val runs many times per screen, so it has to
# start as fast as the one-liner it replaces.


def _config_get(key, default):
    from . import config
    print(config.get_text(key, default))


def _config_set(key, value):
    from . import config
    config.set_text(key, value)


def _steinberg_licenses(prefix):
    from . import licenses
    print(licenses.steinberg_state(prefix))


def _plugin_licenses(prefix):
    from . import licenses
    text = licenses.format_plugins(licenses.active_plugins(prefix))
    if text:
        print(text)


def _manifest():
    from . import manifest
    manifest.main()


def _status():
    from .cli import status
    status.show()


def _header():
    from .cli import header
    header.show()


def _configure_graphics():
    from .cli import graphics
    graphics.configure()


def _apply_graphics_settings():
    from . import graphics, ui
    graphics.apply_settings(ui.echo)


def _apply_prefix_settings():
    from . import prefix
    prefix.apply_settings()


def _map_folder(host_folder="", map_type=""):
    from .cli import folders
    return folders.map_folder(host_folder, map_type)


def _manage_folder_mappings():
    from .cli import folders
    folders.manage()


def _export_keycommands():
    from .cli import keycommands
    keycommands.export()


def _import_keycommands():
    from .cli import keycommands
    keycommands.import_()


def _manage_keycommands():
    from .cli import keycommands
    keycommands.manage()


def _run_custom_exe(selected=""):
    from .cli import tools
    tools.run_custom_exe(selected)


def _enable_ntsync():
    from .cli import tools
    return tools.enable_ntsync()


def _manage_settings():
    from .cli import tools
    tools.manage_settings()


def _check_for_updates():
    from .cli import tools
    tools.check_for_updates()


def _pending_updates():
    from .cli import tools
    print(tools.pending_updates())


def _unknown_argument(arg):
    from .cli import usage
    usage.unknown_argument(arg)


def _flag(args, flag):
    """Whether the Bash caller passed `flag` (e.g. --quiet); other arguments are ignored, as in Bash."""
    return flag in args


def _refresh_launchers(*args):
    from .cli import update
    update.refresh_launchers(pause=not _flag(args, "--no-pause"))


def _update_wine_engine():
    from .cli import engine
    return engine.update_wine_engine()


def _rebuild_wine():
    from .cli import engine
    return engine.rebuild_wine()


def _fix_machine_identity(*args):
    from .cli import engine
    return engine.fix_machine_identity(quiet=_flag(args, "--quiet"))


def _setup_gpu_access(*args):
    from .cli import engine
    return engine.setup_gpu_access(quiet=_flag(args, "--quiet"))


def _manage_wine():
    from .cli import wine_tools
    wine_tools.manage()


def _post_update(old_head=""):
    from .cli import update
    return update.post_update(old_head)


def _update_torquio(*args):
    """Exit code 100 (update.UPDATED) tells the Bash caller to exec the updated copy with --post-update."""
    from .cli import update
    return update.update_torquio(menu=_flag(args, "--menu"))


def _uninstall():
    from .cli import uninstall
    return uninstall.main()


def _export_logs():
    from .cli import tools
    tools.export_logs()


# command: (function, number of required arguments, number of optional ones)
COMMANDS = {
    "config-get": (_config_get, 2, 0),
    "config-set": (_config_set, 2, 0),
    "steinberg-licenses": (_steinberg_licenses, 1, 0),
    "plugin-licenses": (_plugin_licenses, 1, 0),
    "manifest": (_manifest, 0, 0),
    "export-logs": (_export_logs, 0, 0),
    "status": (_status, 0, 0),
    "header": (_header, 0, 0),
    "configure-graphics": (_configure_graphics, 0, 0),
    "apply-graphics-settings": (_apply_graphics_settings, 0, 0),
    "apply-prefix-settings": (_apply_prefix_settings, 0, 0),
    "map-folder": (_map_folder, 0, 2),
    "manage-folder-mappings": (_manage_folder_mappings, 0, 0),
    "export-keycommands": (_export_keycommands, 0, 0),
    "import-keycommands": (_import_keycommands, 0, 0),
    "manage-keycommands": (_manage_keycommands, 0, 0),
    "run-custom-exe": (_run_custom_exe, 0, 1),
    "enable-ntsync": (_enable_ntsync, 0, 0),
    "manage-settings": (_manage_settings, 0, 0),
    "check-for-updates": (_check_for_updates, 0, 0),
    "pending-updates": (_pending_updates, 0, 0),
    "refresh-launchers": (_refresh_launchers, 0, 9),
    "update-wine-engine": (_update_wine_engine, 0, 0),
    "rebuild-wine": (_rebuild_wine, 0, 0),
    "fix-machine-identity": (_fix_machine_identity, 0, 9),
    "setup-gpu-access": (_setup_gpu_access, 0, 9),
    "manage-wine": (_manage_wine, 0, 0),
    "post-update": (_post_update, 0, 1),
    "update-torquio": (_update_torquio, 0, 9),
    "uninstall": (_uninstall, 0, 9),
    "unknown-argument": (_unknown_argument, 1, 0),
}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in COMMANDS:
        print(f"usage: torquio_py {{{','.join(COMMANDS)}}} ...", file=sys.stderr)
        return 2
    function, required, optional = COMMANDS[argv[0]]
    args = argv[1:]
    if not required <= len(args) <= required + optional:
        print(f"torquio_py {argv[0]}: wrong number of arguments", file=sys.stderr)
        return 2
    result = function(*args)
    return result if isinstance(result, int) else 0


def run_main():
    """main() with Ctrl+C handled like a Bash command: no traceback, and the process ends by SIGINT, so the
    Bash script that called it stops too (as it did when this was Bash)."""
    try:
        code = main()
    except KeyboardInterrupt:
        import os
        import signal
        sys.stdout.flush()
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        os.kill(os.getpid(), signal.SIGINT)
        code = 130
    sys.exit(code)


if __name__ == "__main__":
    run_main()
