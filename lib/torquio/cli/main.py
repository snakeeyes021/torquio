"""`torquio`: the flags and the main menu."""
import os
import sys

from .. import config, container, paths, prefix, run, session_log, ui
from ..ui import RESET, WINE, YELLOW, echo
from . import usage

def script(name):
    return os.path.join(paths.repo_dir(), "scripts", name)


def run_installer(args=()):
    return run.interactive([script("install.sh"), *args])


def run_uninstaller(args=()):
    return run.interactive([script("cleanup.sh"), *args])


def wine_program(program, freetype=True):
    ft = config.get_text("freetype_interpreter", "40") if freetype else None
    prefix.enter_visibly(prefix.env_script(ft) + program)


def exec_post_update(old_head, menu):
    """Hand over to the updated copy of Torquio (what the update changed takes effect from here on)."""
    sys.stdout.flush()
    sys.stderr.flush()
    torquio = os.path.join(paths.repo_dir(), "torquio")
    os.execv(torquio, [torquio, "--post-update", old_head] + (["--menu"] if menu else []))


def update(menu):
    from . import update as update_cli
    old_head = run.capture(["git", "-C", paths.repo_dir(), "rev-parse", "HEAD"])[1].strip()
    code = update_cli.update_torquio(menu=menu)
    if code == update_cli.UPDATED:
        exec_post_update(old_head, menu)
    return code


def pause_and_clear():
    echo()
    ui.pause("Press [Enter] to return to the main menu...")
    ui.clear()


def show_menu():
    from . import folders, graphics as graphics_cli, header, keycommands, status, tools, update as update_cli, \
        wine_tools
    tools.check_for_updates()
    while True:
        header.show()
        echo()
        env_active = container.exists() and os.path.isfile(os.path.join(paths.prefix_dir(), ".torquio_core_installed"))
        updates = tools.pending_updates()
        if updates.isdigit() and int(updates) > 0:
            option = 9 if env_active else 4
            changes = "1 change" if int(updates) == 1 else f"{updates} changes"
            echo(f"  {YELLOW}Torquio update available ({changes}): choose {option}) Update Torquio, or run 'torquio -u'.{RESET}")
            echo()
        if env_active:
            labels = ["Reinstall/Repair Torquio Environment", "Uninstall/Wipe Torquio", "Status Dashboard",
                      "Configure Graphics & Scaling", "Fix Icons & Refresh Launchers", "Manage Folder Mappings (Map/Unmap)",
                      "Manage Dorico Key Commands", "Wine Tools & Maintenance", "Update Torquio",
                      "Export Logs (for bug reports)", "Settings", "Exit"]
        else:
            labels = ["Install Torquio Environment", "Clean/Remove Torquio", "Status Dashboard", "Update Torquio",
                      "Export Logs (for bug reports)", "Settings", "Exit"]
        for i, label in enumerate(labels, 1):
            echo(f"  {WINE}{i}){RESET} {label}")
        echo()
        choice = ui.ask(f"Select an option (1-{len(labels)}): ")
        echo()
        action = labels[int(choice) - 1] if choice in [str(i) for i in range(1, len(labels) + 1)] else None
        if action in ("Reinstall/Repair Torquio Environment", "Install Torquio Environment"):
            code = run_installer()
            if code == 10:
                pause_and_clear()
                continue
            if code != 0:
                return code
        elif action in ("Uninstall/Wipe Torquio", "Clean/Remove Torquio"):
            code = run_uninstaller()
            if code == 0:
                ui.clear()
                continue
            if code == 10:
                pause_and_clear()
                continue
            return code
        elif action == "Status Dashboard":
            status.show()
        elif action == "Configure Graphics & Scaling":
            graphics_cli.configure()
            ui.clear()
            continue
        elif action == "Fix Icons & Refresh Launchers":
            update_cli.refresh_launchers()
            ui.clear()
            continue
        elif action == "Manage Folder Mappings (Map/Unmap)":
            folders.manage()
            ui.clear()
            continue
        elif action == "Manage Dorico Key Commands":
            keycommands.manage()
            ui.clear()
            continue
        elif action == "Wine Tools & Maintenance":
            wine_tools.manage()
            ui.clear()
            continue
        elif action == "Update Torquio":
            update(menu=True)
        elif action == "Export Logs (for bug reports)":
            tools.export_logs()
        elif action == "Settings":
            tools.manage_settings()
            ui.clear()
            continue
        elif action == "Exit":
            return 0
        else:
            print(f"Invalid option. Please choose 1-{len(labels)}.")
        pause_and_clear()


def environment():
    """What scripts/common.sh set up for everything Torquio runs: the same variables (exported, so the
    installer, the uninstaller and the container's scripts see them), and Torquio's folders."""
    os.environ["TORQUIO_CONTAINER_NAME"] = paths.container_name()
    os.environ["TORQUIO_DATA_DIR"] = paths.data_dir()
    os.environ["TORQUIO_CACHE_DIR"] = paths.cache_dir()
    os.environ["TORQUIO_PREFIX_DIR"] = paths.prefix_dir()
    os.environ["TORQUIO_BUILD_DIR"] = paths.build_dir()
    os.environ["TORQUIO_INSTALLERS_DIR"] = paths.installers_dir()
    os.environ["WINE_CUSTOM_PATH"] = paths.WINE_CUSTOM_PATH
    os.environ["WINE_CUSTOM_BIN"] = paths.WINE_CUSTOM_BIN
    os.environ["TORQUIO_IMAGE_REPO"] = paths.image_repo()
    # Globally disable winemenubuilder to prevent host desktop pollution
    os.environ["WINEDLLOVERRIDES"] = "winemenubuilder.exe=d"
    for directory in (paths.data_dir(), paths.cache_dir(), paths.installers_dir()):
        os.makedirs(directory, exist_ok=True)


def main(argv):
    session_log.start("main", "Main", argv[0])
    environment()
    args = argv[1:]
    try:
        return run_command(args)
    except KeyboardInterrupt:
        import signal
        sys.stdout.flush()
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        os.kill(os.getpid(), signal.SIGINT)
        return 130


def run_command(args):
    from . import engine as engine_cli, folders, graphics as graphics_cli, keycommands, status, tools, \
        update as update_cli
    if not args:
        ui.clear()
        return show_menu()
    flag = args[0]
    if flag in ("-i", "--install", "--reinstall"):
        return run_installer(args[1:])
    if flag in ("-r", "--remove", "--uninstall"):
        return run_uninstaller(args[1:])
    if flag in ("-f", "--fix-icons"):
        code = run.interactive(["distrobox", "enter", paths.container_name(), "--", "bash", "-c",
                                f'cd "{paths.repo_dir()}" && ./scripts/2-install/extract_icons.sh'])
        run.check(code, True)
        run.interactive(["update-desktop-database", os.path.join(paths.home(), ".local/share/applications/")],
                        stdout=run.DEVNULL, stderr=run.DEVNULL)
        return 0
    if flag in ("-g", "--graphics"):
        graphics_cli.configure()
        return 0
    if flag in ("-s", "--status"):
        status.show()
        return 0
    if flag in ("-u", "--update"):
        return update(menu=False)
    if flag == "--post-update":
        code = update_cli.post_update(args[1] if len(args) > 1 else "")
        if len(args) > 2 and args[2] == "--menu":
            echo()
            ui.pause("Press [Enter] to return to the main menu...")
            ui.clear()
            return show_menu()
        return code
    if flag in ("-d", "--map_folder"):
        return folders.map_folder(args[1] if len(args) > 1 else "", args[2] if len(args) > 2 else "")
    if flag in ("-l", "--export-logs", "--export_logs"):
        tools.export_logs()
        return 0
    if flag == "--manifest":
        from .. import manifest
        manifest.main()
        return 0
    if flag in ("-x", "--export_key_commands"):
        keycommands.export()
        return 0
    if flag in ("-m", "--import_key_commands"):
        keycommands.import_()
        return 0
    if flag in ("-w", "--winecfg"):
        wine_program("winecfg")
        return 0
    if flag in ("-k", "--kill_wine"):
        print("Shutting down Wine server...")
        wine_program("wineserver -k && wineserver -w", freetype=False)
        print("Wine server shutdown complete.")
        return 0
    if flag in ("-b", "--reboot"):
        print("Rebooting Wine prefix...")
        wine_program("wineboot -r")
        print("Prefix reboot completed.")
        return 0
    if flag in ("-e", "--execute", "--run"):
        tools.run_custom_exe(args[1] if len(args) > 1 else "")
        return 0
    if flag in ("--rebuild-wine", "--rebuild_wine"):
        return engine_cli.rebuild_wine()
    if flag in ("--fix-identity", "--fix_identity"):
        return engine_cli.fix_machine_identity()
    if flag in ("--setup-gpu", "--setup_gpu"):
        return engine_cli.setup_gpu_access()
    if flag in ("--enable-ntsync", "--enable_ntsync"):
        return tools.enable_ntsync()
    usage.unknown_argument(flag)
    return 1
