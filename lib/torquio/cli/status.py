"""The Status Dashboard (main menu option 3, `torquio --status`)."""
import glob
import os
import stat

from .. import config, container, engine, graphics, identity, paths, run, versions
from ..ui import BLUE, DARK_GRAY, GRAY, GREEN, RED, RESET, WINE, YELLOW, echo

RULE = f"{GRAY}================================================================{RESET}"

# One trip into the container for the GPUs, NVIDIA's libraries and Wine's dxcore
GPU_PROBE = f"""
            vulkaninfo --summary 2>/dev/null | awk -F' = ' '/deviceType/ {{t=$2}} /deviceName/ {{print "gpu=" t "|" $2}}'
            [ -e /usr/lib/x86_64-linux-gnu/libGLX_nvidia.so.0 ] && echo nvidia=yes
            grep -qa 'builtin d3d12 is in use' {paths.WINE_CUSTOM_PATH}/lib/wine/x86_64-windows/dxcore.dll 2>/dev/null && echo dxcore=patched
            command -v vulkaninfo >/dev/null && echo vulkaninfo=yes"""


def on(value):
    """A boolean setting as the screens test it: true (any case) or 1."""
    return value.lower() == "true" or value == "1"


def session_type():
    return os.environ.get("XDG_SESSION_TYPE", "")


def container_section(listing):
    echo(f"{BLUE}Distrobox Container Status:{RESET}")
    name = paths.container_name()
    if not container.exists(listing):
        echo(f"  - Container: {DARK_GRAY}{name}{RESET} ({RED}Not Created{RESET})")
        return
    echo(f"  - Container: {DARK_GRAY}{name}{RESET} (Active: {GREEN}{container.status(listing) or 'running'}{RESET})")
    image = container.image()
    expected = engine.prebuilt_image()
    tag = image.rsplit(":", 1)[-1]
    update = "(Wine Tools > Update / Rebuild Wine Engine)"
    if not engine.is_prebuilt(image):
        if engine.outdated(image):
            echo(f"  - Wine Engine: {YELLOW}Compiled locally, update available{RESET} {update}")
        else:
            echo(f"  - Wine Engine: {WINE}Compiled locally{RESET}")
    elif expected and image != expected:
        echo(f"  - Wine Engine: {YELLOW}Prebuilt {tag}, update available{RESET} {update}")
    else:
        echo(f"  - Wine Engine: {GREEN}Prebuilt {tag}{RESET}")
    machine_id = identity.container_machine_id()
    if machine_id == identity.derived_machine_id():
        echo(f"  - Computer Identity: {GREEN}Stable{RESET} (derived from this computer)")
    elif len(machine_id) == 32:
        echo(f"  - Computer Identity: {YELLOW}Specific to this container{RESET} (run 'torquio --fix-identity')")


def prefix_section():
    echo(f"{BLUE}Wine Prefix Status:{RESET}")
    prefix = paths.prefix_dir()
    if os.path.isdir(prefix):
        size = (run.capture(["du", "-sh", prefix])[1].split() or [""])[0]
        echo(f"  - Wine Prefix: {DARK_GRAY}{prefix}{RESET} (Size: {WINE}{size}{RESET})")
        if os.path.isfile(os.path.join(prefix, ".torquio_core_installed")):
            echo(f"  - Core Wine Dependencies:   {GREEN}Installed{RESET} (dotnet48, vcrun2019, wine-icu)")
        else:
            echo(f"  - Core Wine Dependencies:   {RED}Incomplete{RESET} (Run installation to fix)")
    else:
        echo(f"  - Wine Prefix: {RED}Not Initialized{RESET} (Run installation to create)")

    ntsync = f"{GRAY}Disabled (wineserver fallback){RESET}"
    if os.path.exists("/dev/ntsync"):
        ntsync = f"{GREEN}Available (/dev/ntsync active){RESET}"
    elif is_char_device("/run/host/dev/ntsync"):
        ntsync = f"{GREEN}Available (/run/host/dev/ntsync active){RESET}"
    elif run.succeeds(["modinfo", "ntsync"]):
        ntsync = f"{YELLOW}Supported, but dormant (Run './torquio --enable-ntsync' to activate){RESET}"
    echo(f"  - Kernel Fast Sync (ntsync):   {ntsync}")


def is_char_device(path):
    try:
        return stat.S_ISCHR(os.stat(path).st_mode)
    except OSError:
        return False


def preferences_section():
    echo(f"{BLUE}Configuration Preferences:{RESET}")
    x11 = session_type() == "x11"
    manage = "N/A (Wayland Only)" if x11 else ("On" if on(config.get_text("manage_graphics", "false")) else "Off")
    freetype = config.get_text("freetype_interpreter", "40")
    match = "N/A (Wayland Only)" if x11 else ("On" if on(config.get_text("match_physical_dpi", "false")) else "Off")
    echo(f"  - Auto Manage Graphics:        {WINE}{manage}{RESET}")
    echo(f"  - Match Physical DPI:          {WINE}{match}{RESET}")
    echo(f"  - FreeType Interpreter:        {WINE}v{freetype}{RESET}")


def de_display(de):
    """The desktop's name with the session type added, as the screens show it."""
    shown = de or "Unknown"
    if any(d in shown for d in ("GNOME", "KDE", "COSMIC")) and "X11" not in shown and "Wayland" not in shown:
        shown += " (Wayland)" if session_type() == "wayland" else " (X11)"
    return shown


def graphics_section():
    echo(f"{BLUE}Graphics & Display Status:{RESET}")
    data = graphics.query()
    de = graphics.field(data, "de", "string")
    connector = graphics.field(data, "connector", "string")
    scale = graphics.field(data, "scale", "number")
    w_px = graphics.field(data, "width", "int")
    h_px = graphics.field(data, "height", "int")
    target_dpi = graphics.field(data, "target_wine_dpi", "int")
    rec_formula = graphics.field(data, "rec_formula", "string")

    echo(f"  - Desktop Environment:         {WINE}{de_display(de)}{RESET}")
    if w_px and graphics.is_int(w_px) and int(w_px) > 0:
        echo(f"  - Active Main Monitor:         {WINE}{w_px}x{h_px}{RESET} ({connector or 'Unknown'})")
        echo(f"  - Desktop Scale Factor:        {WINE}{graphics.scale_percent(scale)}% ({scale}){RESET}")
    else:
        echo(f"  - Active Main Monitor:         {RED}Unknown / Undetected{RESET}")
        echo(f"  - Desktop Scale Factor:        {RED}Unknown / Undetected{RESET}")

    sys_policy, effective, rec_policy = graphics.policies(de, scale, session_type())
    echo(f"  - XWayland Policy Setting:     {WINE}{sys_policy}{RESET}")
    echo(f"  - Effective XWayland Scaling:  {WINE}{effective}{RESET}")
    echo(f"  - Current Wine DPI:            {WINE}{graphics.wine_prefix_dpi()} DPI{RESET}")

    if session_type() == "x11":
        echo(f"  - Recommended Scaling Policy: {WINE}N/A (Native X11 Session){RESET}")
        echo(f"  - Recommended Wine DPI:        {WINE}Manual Config Required{RESET}")
    elif graphics.supported(data):
        echo(f"  - Recommended XWayland Policy: {GREEN}{rec_policy}{RESET}")
        echo(f"  - Recommended Wine DPI:        {GREEN}{target_dpi or '96'} DPI{RESET} "
             f"({rec_formula or 'Handled natively by X11'})")
    else:
        echo(f"  - Graphics Automation:         {RED}Unsupported DE{RESET}")


def gpu_section(listing):
    echo(f"{BLUE}GPU for AI Plug-ins (e.g. Cantai):{RESET}")
    if not container.exists(listing):
        echo(f"  - Status:                      {RED}Container not created{RESET}")
        return
    ai_ready = True
    probe = container.enter_bash(GPU_PROBE).splitlines()
    gpus = [line[4:] for line in probe if line.startswith("gpu=")]
    gpus = [g for g in gpus if not g.startswith("PHYSICAL_DEVICE_TYPE_CPU")]
    if gpus:
        for g in gpus:
            kind = "dedicated" if "DISCRETE" in g.split("|", 1)[0] else "integrated"
            echo(f"  - GPU:                         {WINE}{g.split('|', 1)[-1]}{RESET} {GRAY}({kind}){RESET}")
    elif any(line.startswith("vulkaninfo=yes") for line in probe):
        echo(f"  - GPU:                         {RED}None found{RESET}")
        ai_ready = False
    else:
        echo(f"  - GPU:                         {YELLOW}Unknown{RESET} (run 'torquio --setup-gpu')")
        ai_ready = False
    if os.path.exists("/proc/driver/nvidia/version"):
        if any(line.startswith("nvidia=yes") for line in probe):
            echo(f"  - NVIDIA Access:               {GREEN}Enabled{RESET}")
        else:
            echo(f"  - NVIDIA Access:               {YELLOW}Not set up{RESET} (run 'torquio --setup-gpu')")

    ai_gpu = config.get_text("ai_gpu", "auto")
    if ai_gpu == "auto":
        picked = auto_gpu(gpus)
        echo(f"  - Setting:                     {WINE}Automatic{RESET}" + (f" (uses {picked})" if picked else ""))
    elif ai_gpu == "off":
        echo(f"  - Setting:                     {WINE}Off{RESET} (AI plug-ins use the CPU)")
        ai_ready = False
    else:
        echo(f"  - Setting:                     {WINE}{ai_gpu}{RESET}")

    downloaded = glob.glob(os.path.join(glob.escape(paths.data_dir()), "vkd3d-proton", "*", ""))
    if downloaded:
        newest = versions.sort(downloaded)[-1]
        echo(f"  - vkd3d-proton (Direct3D 12):  {GREEN}{os.path.basename(newest.rstrip('/'))}{RESET}")
    else:
        echo(f"  - vkd3d-proton (Direct3D 12):  {YELLOW}Not downloaded{RESET} (run 'torquio --setup-gpu')")
        ai_ready = False
    if any(line.startswith("dxcore=patched") for line in probe):
        echo(f"  - Wine Engine GPU Support:     {GREEN}Yes{RESET}")
    else:
        echo(f"  - Wine Engine GPU Support:     {YELLOW}Needs a rebuild{RESET} (Wine Tools > Update / Rebuild Wine Engine)")
        ai_ready = False
    cantai = os.path.join(glob.escape(paths.prefix_dir()), "drive_c/users/*/AppData/Local/Cantai/Cantai.exe")
    if not glob.glob(cantai):
        echo(f"  - Cantai:                      {GRAY}Not installed{RESET}")
    elif ai_ready:
        echo(f"  - Cantai:                      {GREEN}Renders on the GPU{RESET}")
    else:
        echo(f"  - Cantai:                      {YELLOW}Renders on the CPU{RESET} (see above)")


def auto_gpu(gpus):
    """The GPU "Automatic" uses: the first dedicated one, otherwise the first integrated one."""
    dedicated = integrated = ""
    for g in gpus:
        fields = g.split("|")
        name = fields[1] if len(fields) > 1 else ""
        if "DISCRETE" in fields[0] and not dedicated:
            dedicated = name
        if "INTEGRATED" in fields[0] and not integrated:
            integrated = name
    return dedicated or integrated


def show():
    echo(RULE)
    echo(f"             {WINE}Torquio Environment Dashboard{RESET}                ")
    echo(RULE)
    echo()
    listing = container.distrobox_list()
    container_section(listing)
    echo()
    prefix_section()
    echo()
    preferences_section()
    echo()
    graphics_section()
    echo()
    gpu_section(listing)
    echo(RULE)
    echo()
