"""`torquio api VERB`: the machine-readable interface for Torquio's GUI (docs/GUI.md). Prints JSON on stdout
and nothing else: no session log header, no colours, no prompts. The GUI runs it on the host (through
`flatpak-spawn --host` from its sandbox) and checks API_VERSION first.

Two kinds of verbs:
- data verbs (`status`, `settings`, `folders`, ...) print one JSON object and exit;
- `task NAME ARGS...` runs a long job (install, update, ...) and prints one JSON event per line:
  {"event": "phase", "text": ...}, {"event": "log", "text": ...}, {"event": "result", ...} and finally
  {"event": "done", "code": N}. The job runs in a child process whose output (and that of everything it runs)
  becomes the log events; it never waits on a prompt: every answer is passed in, and its input is empty.

The GUI asks for a minimum API_VERSION (gui/src/host.py, MIN_API) and offers to update an older Torquio. Bump
API_VERSION when a verb's output changes in a way an older GUI would misread, or when the GUI starts using a verb,
task or field that a released Torquio lacks (then raise MIN_API with it). Additions nothing uses yet don't need
it. 1: v0.6.5 (`version`, `status`); 2: v0.7.0 (everything the first GUI uses)."""
import glob
import json
import os
import re
import signal
import stat
import subprocess
import sys

from . import config, container, engine, graphics, identity, paths, run

API_VERSION = 2

# A task's own markers in its output, turned into events by the parent
PHASE = "::torquio-phase::"
RESULT = "::torquio-result::"
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07")
INSTALLER_PHASE = re.compile(r"^(Phase \d+: .*|=== (.*) ===)$")
# The CLI's step headings as the GUI shows them (None: not a step worth showing)
PHASE_NAMES = [("Installation Manifest", None), ("Creating Distrobox container", "Setting up the container"),
               ("Wine Engine", "Getting the Wine engine"),
               ("Initializing Wine Prefix", "Preparing Windows: fonts, .NET and runtimes (the longest step)"),
               ("Installing Steinberg Components", "Installing Steinberg's components and your plug-ins"),
               ("Performing Host Integration", "Adding Dorico to your desktop"),
               ("Refreshing Launchers & Icons", None), ("Rebuilding Wine Engine", "Compiling the Wine engine"),
               ("Update Torquio", None), ("GPU Access for AI Plug-ins", "Setting up GPU access"),
               ("Export Logs", None)]


def phase_name(heading):
    heading = heading.rstrip(". ")
    for prefix, name in PHASE_NAMES:
        if heading.startswith(prefix):
            return name
    return heading
SETTINGS = {  # setting: (default, kind)
    "manage_graphics": ("false", "bool"),
    "manual_dpi": ("96", "int"),
    "match_physical_dpi": ("false", "bool"),
    "freetype_interpreter": ("40", "choice:40,35"),
    "ai_gpu": ("auto", "text"),
    "check_for_updates": ("true", "bool"),
}
GRAPHICS_SETTINGS = ("manage_graphics", "manual_dpi", "match_physical_dpi", "freetype_interpreter")
WINE_PROGRAMS = {"winecfg": "winecfg", "regedit": "regedit", "control": "wine control", "explorer": "wine explorer",
                 "cmd": "wine cmd"}


class Error(Exception):
    """A request the API refuses; becomes {"error": ...} and exit code 1."""


def phase(text):
    """In a task: start a new step (the GUI shows it as the task's progress)."""
    print(PHASE + text, flush=True)


def result(**values):
    """In a task: data for the GUI (e.g. the file it made)."""
    print(RESULT + json.dumps(values), flush=True)


# ---- data ------------------------------------------------------------------------------------------------------

def version():
    from . import appinfo
    return {"api": API_VERSION, "torquio": appinfo.version(), "branch": appinfo.branch(),
            "repo": paths.repo_dir(), "app_copy": appinfo.is_app_copy()}


def _char_device(path):
    try:
        return stat.S_ISCHR(os.stat(path).st_mode)
    except OSError:
        return False


def _ntsync():
    if os.path.exists("/dev/ntsync") or _char_device("/run/host/dev/ntsync"):
        return "active"
    return "dormant" if run.succeeds(["modinfo", "ntsync"]) else "unavailable"


def _engine(image):
    if not image:
        return {"source": "", "image": "", "update_available": False}
    from_image = engine.from_image(image)
    return {"source": "prebuilt" if from_image else "compiled", "image": image,
            "update_available": engine.outdated(image)}


def _pending_updates():
    from . import appinfo
    if appinfo.is_app_copy():
        return 0  # the app's copy is updated with the app
    code, out = run.capture(["git", "-C", paths.repo_dir(), "rev-list", "--count", "HEAD..@{u}"])
    return int(out.strip()) if code == 0 and out.strip().isdigit() else 0


def _settings():
    values = {}
    for key, (default, kind) in SETTINGS.items():
        text = config.get_text(key, default)
        values[key] = text == "true" if kind == "bool" else text
    return values


def _installed_apps():
    """Which of Dorico and Steinberg's tools are in the prefix."""
    drive_c = os.path.join(paths.prefix_dir(), "drive_c")
    found = lambda *patterns: any(glob.glob(os.path.join(glob.escape(drive_c), p)) for p in patterns)
    return {
        "dorico": found("Program Files/Steinberg/Dorico*/Dorico*.exe"),
        "activation_manager": found("Program Files/Steinberg/Activation Manager/SteinbergActivationManager.exe"),
        "download_assistant": found("Program Files (x86)/Steinberg/Download Assistant/*.exe"),
        "noteperformer": found("Program Files/Common Files/VST3/NotePerformer*.vst3"),
        "cantai": found("users/*/AppData/Local/Cantai/Cantai.exe"),
    }


def status():
    """What the Status Dashboard shows, as data."""
    listing = container.distrobox_list()
    exists = container.exists(listing)
    prefix = paths.prefix_dir()
    machine_id = identity.container_machine_id() if exists else ""
    data = {
        "container": {"name": paths.container_name(), "exists": exists,
                      "status": container.status(listing) if exists else ""},
        "engine": _engine(container.image() if exists else ""),
        "identity": ("stable" if machine_id and machine_id == identity.derived_machine_id()
                     else "container" if len(machine_id) == 32 else ""),
        "prefix": {"path": prefix, "exists": os.path.isdir(prefix),
                   "core_installed": os.path.isfile(os.path.join(prefix, ".torquio_core_installed"))},
        "apps": _installed_apps(),
        "ntsync": _ntsync(),
        "settings": _settings(),
        "session_type": os.environ.get("XDG_SESSION_TYPE", ""),
        "desktop": os.environ.get("XDG_CURRENT_DESKTOP", ""),
        "updates_pending": _pending_updates() if config.get_text("check_for_updates", "true") == "true" else 0,
    }
    data["installed"] = exists and data["prefix"]["core_installed"]
    return data


def running():
    """Whether Dorico or one of Steinberg's programs is open (changing graphics settings restarts Wine)."""
    from .launch.common import apps_running
    return {"running": container.exists() and apps_running()}


def settings(*args):
    """`settings` (all of them) or `settings set KEY VALUE` (graphics settings are applied to the prefix at
    once, which restarts Wine)."""
    if not args:
        return _settings()
    if args[0] != "set" or len(args) != 3:
        raise Error("usage: settings [set KEY VALUE]")
    key, value = args[1], args[2]
    if key not in SETTINGS:
        raise Error(f"unknown setting {key!r}")
    kind = SETTINGS[key][1]
    if kind == "bool" and value not in ("true", "false"):
        raise Error(f"{key} is true or false")
    if kind == "int" and not (value.isascii() and value.isdigit() and 48 <= int(value) <= 480):
        raise Error(f"{key} is a whole number from 48 to 480")
    if kind.startswith("choice:") and value not in kind[len("choice:"):].split(","):
        raise Error(f"{key} is one of {kind[len('choice:'):]}")
    config.set_text(key, value)
    if key in GRAPHICS_SETTINGS:
        graphics.apply_settings(lambda *a: None)
    return _settings()


def _policy_descs():
    from .cli.graphics import cosmic_desc, gnome_desc, kde_desc
    return gnome_desc, kde_desc, cosmic_desc


def _restorable():
    """The desktop's XWayland setting Automated Mode changed and can put back: (desktop, original, current
    descriptions) or None."""
    gnome_desc, kde_desc, cosmic_desc = _policy_descs()
    orig = config.get_text("original_scale_factor", "")
    if orig:
        current = graphics.xwayland_scaling_factor() or "0"
        if current != orig:
            return {"desktop": "GNOME", "original": gnome_desc(orig), "current": gnome_desc(current)}
    orig = config.get_text("original_kde_policy", "")
    if orig:
        current = graphics.kde_xwayland_policy() or "true"
        if current != orig:
            return {"desktop": "KDE", "original": kde_desc(orig), "current": kde_desc(current)}
    orig = config.get_text("original_cosmic_policy", "")
    if orig:
        current = graphics.cosmic_xwayland_policy() or "none"
        if current != orig:
            return {"desktop": "COSMIC", "original": cosmic_desc(orig), "current": cosmic_desc(current)}
    return None


def restore_desktop_scaling():
    """Put back the desktop's XWayland setting Automated Mode changed (as switching to Manual Mode offers)."""
    orig = config.get_text("original_scale_factor", "")
    if orig and (graphics.xwayland_scaling_factor() or "0") != orig:
        graphics.set_gnome_xwayland_factor(orig)
    orig = config.get_text("original_kde_policy", "")
    if orig and (graphics.kde_xwayland_policy() or "true") != orig:
        graphics.set_kde_xwayland_policy(orig)
    orig = config.get_text("original_cosmic_policy", "")
    if orig and (graphics.cosmic_xwayland_policy() or "none") != orig:
        graphics.write_cosmic_policy(None if orig == "none" else orig)
    for key in ("original_scale_factor", "original_kde_policy", "original_cosmic_policy"):
        config.set_text(key, "")


def display(*args):
    """The monitor, scale and desktop as Torquio sees them, and what it would set. `display restore` puts the
    desktop's XWayland setting back."""
    if args[:1] == ("restore",):
        restore_desktop_scaling()
    try:
        data = json.loads(graphics.query() or "{}")
    except ValueError:
        data = {}
    return {"graphics": data, "supported": graphics.supported(json.dumps(data)) if data else False,
            "session_type": os.environ.get("XDG_SESSION_TYPE", ""), "wine_dpi": graphics.wine_prefix_dpi(),
            "restorable": _restorable()}


def folders(*args):
    """`folders` lists the mapped folders; `folders map PATH drive|desktop` and `folders unmap drive LETTER` /
    `folders unmap desktop PATH` change them."""
    from . import folders as f
    if args[:1] == ("map",) and len(args) == 3 and args[2] in ("drive", "desktop"):
        from .cli import folders as cli_folders
        if not os.path.isdir(args[1]):
            raise Error("That folder doesn't exist.")
        if cli_folders.map_folder(args[1], args[2], strict=False) != 0:
            raise Error("The folder couldn't be mapped.")
    elif args[:1] == ("unmap",) and len(args) == 3 and args[1] == "drive":
        f.unmap_drive(args[2].rstrip(":").lower())
    elif args[:1] == ("unmap",) and len(args) == 3 and args[1] == "desktop":
        if not any(path == args[2] for path, _ in f.desktop_shortcuts()):
            raise Error("That isn't one of the mapped Desktop shortcuts.")
        f.remove_link(args[2])
    elif args:
        raise Error("usage: folders [map PATH drive|desktop | unmap drive LETTER | unmap desktop PATH]")
    drives = [{"letter": letter.upper() + ":", "target": target} for letter, target in f.mapped_drives()] \
        if os.path.isdir(f.dosdevices()) else []
    shortcuts = [{"name": os.path.basename(path), "path": path, "target": target}
                 for path, target in f.desktop_shortcuts()]
    return {"drives": drives, "shortcuts": shortcuts, "prefix": os.path.isdir(f.dosdevices())}


def keycommands(*args):
    """`keycommands` (backups in Downloads, whether Dorico has key commands), `keycommands export`,
    `keycommands import PATH` (imported on Dorico's next start)."""
    from .cli import keycommands as k
    if args[:1] == ("export",):
        folder = k.dorico_appdata()
        files = glob.glob(os.path.join(glob.escape(folder), "keycommands_*.json")) if folder else []
        if not files:
            raise Error("Dorico has no custom key commands to export yet.")
        import zipfile
        downloads = k.downloads_dir()
        os.makedirs(downloads, exist_ok=True)
        zip_file = os.path.join(downloads, k.BACKUP_NAME)
        with zipfile.ZipFile(zip_file, "w") as z:
            for name in files:
                z.write(name, os.path.basename(name))
        return {"exported": zip_file, "files": [os.path.basename(n) for n in files]}
    if args[:1] == ("import",) and len(args) == 2:
        if not os.path.isfile(args[1]) or not args[1].endswith((".zip", ".json")):
            raise Error("Choose a key commands backup (.zip or .json).")
        k.stage(args[1])
        return {"staged": args[1]}
    if args:
        raise Error("usage: keycommands [export | import PATH]")
    folder = k.dorico_appdata()
    return {"backups": k.backups_in(k.downloads_dir()), "downloads": k.downloads_dir(),
            "dorico_files": sorted(os.path.basename(n) for n in
                                   glob.glob(os.path.join(glob.escape(folder), "keycommands_*.json"))) if folder else []}


def gpus():
    """The GPUs AI plug-ins can use, NVIDIA access and Cantai's state."""
    from .cli.status import GPU_PROBE, auto_gpu
    exists = container.exists()
    probe = container.enter_bash(GPU_PROBE).splitlines() if exists else []
    found = [line[4:] for line in probe if line.startswith("gpu=") and "PHYSICAL_DEVICE_TYPE_CPU" not in line]
    from . import versions
    vkd3d = glob.glob(os.path.join(glob.escape(paths.data_dir()), "vkd3d-proton", "*", ""))
    return {
        "gpus": [{"name": g.split("|", 1)[-1], "dedicated": "DISCRETE" in g.split("|", 1)[0]} for g in found],
        "automatic": auto_gpu(found),
        "setting": config.get_text("ai_gpu", "auto"),
        "nvidia": {"host": container.has_nvidia_host(), "enabled": any(l == "nvidia=yes" for l in probe)},
        "engine_support": any(l == "dxcore=patched" for l in probe),
        "vkd3d": os.path.basename(versions.sort(vkd3d)[-1].rstrip("/")) if vkd3d else "",
        "cantai": _installed_apps()["cantai"],
    }


def prereqs():
    """What a new install needs: the host's programs and the installers it found."""
    from .cli.install import INSTALLER_PATTERNS, find_installer
    search = [paths.installers_dir(), os.path.join(paths.home(), "Downloads")]
    return {
        "distrobox": run.have("distrobox"),
        "container_manager": "podman" if run.have("podman") else "docker" if run.have("docker") else "",
        "python": ".".join(map(str, sys.version_info[:3])),
        "installers": {key: find_installer(pattern, search) for key, pattern in INSTALLER_PATTERNS.items()},
        "installers_dir": paths.installers_dir(),
        "ntsync": _ntsync(),
        "session_type": os.environ.get("XDG_SESSION_TYPE", ""),
        "desktop": os.environ.get("XDG_CURRENT_DESKTOP", ""),
        "nvidia": container.has_nvidia_host(),
    }


def updates(*args):
    """`updates` (what's waiting on GitHub since the last check), `updates check` (fetch now), `updates daily`
    (fetch if the setting allows and the last check is a day old, as the terminal menu does)."""
    repo = paths.repo_dir()
    if args[:1] == ("check",):
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        if not run.succeeds(["timeout", "20", "git", "-C", repo, "fetch", "--quiet"], env=env):
            raise Error("Couldn't reach GitHub.")
    elif args[:1] == ("daily",):
        from .cli import tools
        tools.check_for_updates()
    elif args:
        raise Error("usage: updates [check | daily]")
    tracking = run.succeeds(["git", "-C", repo, "rev-parse", "--abbrev-ref", "@{u}"])
    log = run.capture(["git", "-C", repo, "log", "--format=%s", "HEAD..@{u}"])[1].splitlines() if tracking else []
    changed = run.capture(["git", "-C", repo, "status", "--porcelain", "--untracked-files=no"])[1].strip()
    ahead = run.capture(["git", "-C", repo, "rev-list", "--count", "@{u}..HEAD"])[1].strip() if tracking else "0"
    return {"tracking": tracking, "commits": log, "local_changes": bool(changed) or ahead not in ("", "0")}


def guards():
    """What the uninstaller warns about: activated licenses and projects inside the prefix."""
    from . import licenses, uninstall
    prefix = paths.prefix_dir()
    try:
        state = licenses.steinberg_state(prefix)
    except Exception:
        state = "unknown the license check failed to run"
    try:
        plugins = [{"name": n, "where": w} for n, w in licenses.active_plugins(prefix) if n]
    except Exception:
        plugins = []
    steinberg = state[len("active\n"):].splitlines() if state.startswith("active\n") else []
    return {"steinberg_active": steinberg, "steinberg_unknown": state.startswith("unknown"), "plugins": plugins,
            "projects": uninstall.prefix_projects() if os.path.isdir(prefix) else [],
            "restorable": _restorable()}


VERBS = {"version": version, "status": status, "running": running, "settings": settings, "display": display,
         "folders": folders, "keycommands": keycommands, "gpus": gpus, "prereqs": prereqs, "updates": updates,
         "guards": guards}


# ---- tasks -----------------------------------------------------------------------------------------------------

def task_install(options="{}"):
    """A new install with the GUI's answers: {"manage": bool, "freetype": "40"|"35", "map_path": PATH,
    "map_type": "drive"|"desktop", "import_path": PATH}."""
    from .cli import folders as cli_folders, install, keycommands as k
    opts = json.loads(options)
    config.set_text("manage_graphics", "true" if opts.get("manage") else "false")
    config.set_text("freetype_interpreter", opts.get("freetype", "40"))
    config.set_text("manual_dpi", config.get_text("manual_dpi", "96"))
    config.set_text("match_physical_dpi", config.get_text("match_physical_dpi", "false"))
    if opts.get("manage"):
        config.set_text("warn_xwayland_change", "true")  # the GUI showed what Automated Mode changes
    code = install.main(["-y", "--no-ntsync"])  # the setup assistant offers NTsync itself
    if code != 0:
        return code
    if opts.get("map_path"):
        phase("Mapping your folder")
        cli_folders.map_folder(opts["map_path"], opts.get("map_type", "drive"), strict=False)
    if opts.get("import_path"):
        k.stage(opts["import_path"])
        print("Your key commands will be imported the first time Dorico starts.")
    return 0


def task_update():
    """Update Torquio (fast-forward to GitHub's version), then refresh everything from the new copy."""
    repo = paths.repo_dir()
    info = updates("check")
    if info["local_changes"]:
        print("Torquio's files have been changed on this computer, so the update can't be applied automatically.")
        return 1
    if not info["commits"]:
        print("Torquio is up to date.")
        return 0
    old_head = run.capture(["git", "-C", repo, "rev-parse", "HEAD"])[1].strip()
    phase("Downloading the update")
    if run.interactive(["git", "-C", repo, "merge", "--ff-only", "--quiet", "@{u}"]) != 0:
        print("The update couldn't be applied. Nothing was changed.")
        return 1
    phase("Refreshing launchers and settings")
    # From the updated copy, which may answer differently (its own --post-update)
    return run.interactive([os.path.join(repo, "torquio"), "--post-update", old_head], stdin=run.DEVNULL)


def task_app_refresh():
    """After the app has placed a new copy of Torquio on the host: launchers, icons, the `torquio` command and the
    prefix's settings, from that copy (what Update Torquio's refresh does), without questions."""
    from .cli import update
    phase("Updating Torquio's files on this computer")
    return update.refresh_after_app_update()


def task_fix_icons():
    """Fix Icons & Refresh Launchers, step by step (what refresh_launchers does)."""
    from . import uninstall
    from .cli.update import install_launchers
    repo, home = paths.repo_dir(), paths.home()
    in_container = lambda script: run.interactive(["distrobox", "enter", paths.container_name(), "--", "bash", "-c",
                                                   f'cd "{repo}" && {script}'])
    phase("Icons and menu entries")
    if in_container("./scripts/2-install/extract_icons.sh") != 0:
        return 1
    uninstall.remove_menu_builder_leftovers()
    run.interactive(["update-desktop-database", os.path.join(home, ".local/share/applications/")],
                    stdout=run.DEVNULL, stderr=run.DEVNULL)
    run.interactive(["update-mime-database", os.path.join(home, ".local/share/mime/")],
                    stdout=run.DEVNULL, stderr=run.DEVNULL)
    phase("Wine prefix settings")
    if in_container("./scripts/2-install/setup_prefix.sh") != 0:
        return 1
    phase("Launchers")
    install_launchers()
    return 0


def task_engine_update():
    from .cli import engine as engine_cli
    image = engine.prebuilt_image()
    if image and container.image() != image:
        phase("Downloading the Wine engine")
        if not container.pull_image(image):
            print("The prebuilt engine for this version of Torquio isn't available yet (it's published within about "
                  "an hour of each update).")
            return 1
        phase("Replacing the container")
        return engine_cli.replace_container(image, strict=False)
    print("Torquio's Wine engine is up to date.")
    return 0


def task_engine_rebuild():
    from .cli import engine as engine_cli
    phase("Compiling the Wine engine (20-40 minutes)")
    return engine_cli.rebuild_wine(strict=False)


def task_setup_gpu():
    from .cli import engine as engine_cli
    if container.has_nvidia_host() and not container.has_nvidia_libraries():
        phase("Re-creating the container with NVIDIA access")
        if engine_cli.replace_container(strict=False) != 0:
            return 1
    phase("Setting up GPU access")
    return engine_cli.setup_gpu_access(quiet=True, strict=False)


def task_ntsync():
    """Load and persist the ntsync module (pkexec: the desktop asks for the password)."""
    if _ntsync() == "active":
        print("Kernel fast sync is already active.")
        return 0
    if _ntsync() == "unavailable":
        print("This kernel has no ntsync module (Linux 6.14 or newer with CONFIG_NTSYNC is needed).")
        return 1
    code = run.interactive(["pkexec", "sh", "-c",
                            "modprobe ntsync && echo ntsync > /etc/modules-load.d/ntsync.conf"])
    print("Kernel fast sync is active." if code == 0 else "Kernel fast sync wasn't enabled.")
    return code


def task_logs():
    from . import logs
    zip_file = logs.write_zip()
    result(path=zip_file)
    print(f"Saved {zip_file}")
    return 0


def task_wine(name, *args):
    """A Wine program in the prefix (winecfg, regedit, control, explorer, cmd; `exe PATH`; `reboot`;
    `shutdown`)."""
    from . import prefix
    freetype = config.get_text("freetype_interpreter", "40")
    import shlex
    if name == "reboot":
        return prefix.enter_visibly(prefix.env_script(freetype) + "wineboot -r")
    if name == "shutdown":
        return prefix.enter_visibly(prefix.env_script() + "wineserver -k && wineserver -w")
    if name == "exe" and args:
        windows = prefix.windows_path(args[0])
        if not windows:
            print(f"Wine couldn't find {args[0]}")
            return 1
        program = (f"msiexec /i {shlex.quote(windows)}" if args[0].lower().endswith(".msi")
                   else shlex.quote(windows))
        # A program's own exit code isn't Torquio's to judge (installers return 3010 and the like)
        prefix.enter_visibly(prefix.env_script(freetype) + f"wine {program}")
        return 0
    if name in WINE_PROGRAMS:
        return prefix.enter_visibly(prefix.env_script(freetype) + WINE_PROGRAMS[name])
    print(f"Unknown program {name}")
    return 1


def task_uninstall(restore="true", app="keep"):
    """Everything the uninstaller removes, after the GUI's checks and confirmation (`restore`: put back the
    desktop's XWayland setting; `app`: "remove" also removes the app's copy of Torquio, last, for someone
    uninstalling the app too; otherwise it stays, and the app puts it back on its next start anyway)."""
    from . import uninstall
    name = paths.container_name()
    if restore == "true" and _restorable():
        phase("Restoring your desktop's scaling setting")
        restore_desktop_scaling()
    phase("Removing the container")
    run.interactive(["distrobox", "rm", name, "--force"])
    for mgr in ("podman", "docker"):
        if run.have(mgr):
            for image in uninstall.container_images(mgr):
                if run.succeeds([mgr, "rmi", image]):
                    print(f"Removed container image {image}")
    phase("Removing Torquio's data")
    uninstall.remove_data()
    phase("Removing launchers and file types")
    uninstall.remove_integrations()
    uninstall.remove_desktop_shortcuts()
    home = paths.home()
    run.interactive(["update-desktop-database", os.path.join(home, ".local/share/applications/")])
    run.interactive(["update-mime-database", os.path.join(home, ".local/share/mime/")])
    if run.have("gtk-update-icon-cache"):
        run.interactive(["gtk-update-icon-cache", "-f", "-t", os.path.join(home, ".local/share/icons/hicolor/")])
    if app == "remove":
        uninstall.remove_app_copy()
    print("Torquio has been removed.")
    return 0


TASKS = {"install": task_install, "update": task_update, "fix-icons": task_fix_icons,
         "app-refresh": task_app_refresh,
         "engine-update": task_engine_update, "engine-rebuild": task_engine_rebuild, "setup-gpu": task_setup_gpu,
         "ntsync": task_ntsync, "logs": task_logs, "wine": task_wine, "uninstall": task_uninstall}


class _Events:
    """Events on stdout. If the GUI goes away mid-task (its window closed, the app quit), stdout breaks; the task
    must still finish (an update half applied or a container half replaced is worse than no answer), so from then
    on events are dropped and the task's output only goes to its session log."""
    gone = False


def _emit(event, **fields):
    if _Events.gone:
        return
    try:
        sys.stdout.write(json.dumps(dict(event=event, **fields)) + "\n")
        sys.stdout.flush()
    except (BrokenPipeError, OSError):
        _Events.gone = True
        try:
            # Point stdout at nothing, so Python's own flush at exit doesn't fail again
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except OSError:
            pass


# One task at a time: two would fight over the container (engine update, install, uninstall...)
TASK_LOCK = "task.lock"


def _task_lock():
    """The open lock file if this is the only running task, else None."""
    import fcntl
    os.makedirs(paths.cache_dir(), exist_ok=True)
    lock = open(os.path.join(paths.cache_dir(), TASK_LOCK), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.close()
        return None
    return lock


def run_task(name, args):
    """The parent side: run the task in a child and turn its output into events."""
    if name not in TASKS:
        _emit("done", code=2, error=f"unknown task {name!r}")
        return 2
    lock = _task_lock() if name != "wine" else True  # Wine's tools stay open; they don't take the lock
    if lock is None:
        _emit("log", text="Another Torquio task is still running. Try again when it has finished.")
        _emit("done", code=3, error="busy")
        return 3
    signal.signal(signal.SIGHUP, signal.SIG_IGN)  # the GUI going away doesn't stop the task
    env = dict(os.environ, PYTHONUNBUFFERED="1", TERM="dumb", NO_COLOR="1")
    # Its own session, so a signal meant for the GUI's process group doesn't stop it halfway
    child = subprocess.Popen([os.path.join(paths.repo_dir(), "torquio"), "api", "_task", name, *args],
                             stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
                             start_new_session=True)
    for raw in iter(child.stdout.readline, b""):
        line = ANSI.sub("", raw.decode("utf-8", "replace")).rstrip("\r\n")
        line = line.split("\r")[-1]  # progress bars redraw with \r: keep the last state
        if line.startswith(PHASE):
            _emit("phase", text=line[len(PHASE):])
        elif line.startswith(RESULT):
            try:
                _emit("result", **json.loads(line[len(RESULT):]))
            except ValueError:
                pass
        elif line.strip():
            m = INSTALLER_PHASE.match(line.strip())
            if m and "Log Started" not in line:
                name = phase_name(m.group(1).split(": ", 1)[-1] if m.group(1).startswith("Phase") else m.group(2))
                if name:
                    _emit("phase", text=name)
            _emit("log", text=line)
    code = child.wait()
    _emit("done", code=code)
    return code


def _quietly(function, *args):
    """function(*args) with whatever it (or a program it runs) prints sent to stderr, so a data verb's stdout is
    only its JSON (the CLI's helpers, such as folder mapping, print for the terminal)."""
    sys.stdout.flush()
    try:
        saved = os.dup(1)
    except OSError:  # no real stdout (tests)
        return function(*args)
    os.dup2(2, 1)
    try:
        return function(*args)
    finally:
        sys.stdout.flush()
        os.dup2(saved, 1)
        os.close(saved)


def main(args):
    """Returns the exit code: 0, 1 for a refused request ({"error": ...}), 2 for an unknown verb."""
    verb = args[0] if args else ""
    if verb == "task":
        return run_task(args[1] if len(args) > 1 else "", args[2:])
    if verb == "_task":
        from . import session_log
        session_log.start("gui", f"GUI {args[1]}", "torquio api task")
        code = TASKS[args[1]](*args[2:])
        return code if isinstance(code, int) else 0
    if verb not in VERBS:
        json.dump({"error": f"unknown verb {verb!r}", "verbs": sorted(VERBS) + ["task"]}, sys.stdout)
        print()
        return 2
    try:
        data = _quietly(VERBS[verb], *args[1:])
    except Error as e:
        json.dump({"error": str(e)}, sys.stdout)
        print()
        return 1
    except TypeError:
        json.dump({"error": f"wrong arguments for {verb}"}, sys.stdout)
        print()
        return 1
    json.dump(data, sys.stdout)
    print()
    return 0
