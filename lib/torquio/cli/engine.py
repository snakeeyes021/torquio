"""The Wine engine and the container: updating, rebuilding, re-creating, GPU access and the computer identity.

`strict` mirrors the Bash version's set -e: True where it was in force, so a failing step stops Torquio with
that exit code exactly where it did; False inside functions Bash called from `||`, `&&` or `if`, where set -e
doesn't apply (and doesn't apply to anything they call either).
"""
import os
import time

from .. import config, container, engine, identity, licenses, paths, prefix, run, ui
from ..ui import BLUE, GRAY, GREEN, RED, RESET, WINE, YELLOW, echo


def _enter(*cmd, name=None, **kwargs):
    return run.interactive(["distrobox", "enter", name or paths.container_name(), "--", *cmd], **kwargs)


def _quiet(cmd, **kwargs):
    """cmd >/dev/null 2>&1"""
    return run.interactive(cmd, stdout=run.DEVNULL, stderr=run.DEVNULL, **kwargs)


def container_gpu_setup():
    _enter("bash", "-c", f'cd "{paths.repo_dir()}" && ./scripts/1-build/container_gpu_setup.sh')


def replace_container(image="", strict=True):
    """Re-create the Torquio container from IMAGE (an updated prebuilt engine) or, without one, from the image
    it came from: the prebuilt image, or for a locally compiled engine a snapshot of the container itself. The
    new container gets the host's NVIDIA libraries when there are any, and is checked before it replaces the
    old one. The Wine prefix lives outside the container and isn't touched. Returns 0 or 1."""
    name = paths.container_name()
    mgr = container.manager()
    current = container.image()
    new = f"{name}-new"
    snapshot = ""
    if not image and engine.is_prebuilt(current):
        image = current
    machine_id = identity.container_machine_id()
    print("Stopping Wine and the container...")
    _enter("bash", "-c", f'export PATH="{paths.WINE_CUSTOM_BIN}:$PATH"; wineserver -k 2>/dev/null; wineserver -w 2>/dev/null')
    _quiet(["distrobox", "stop", name, "--yes"])
    if not image:
        store = os.path.join(paths.home(), ".local/share/containers")
        if not os.path.isdir(store):
            store = paths.home()
        # The snapshot needs about as much space as the container (~7 GB) until the old container is removed.
        st = os.statvfs(store)
        if st.f_bavail * st.f_frsize // 1024 < 10 * 1024 * 1024:
            echo(f"{RED}Not enough free disk space (10 GB needed); nothing was changed.{RESET}")
            return 1
        snapshot = f"localhost/{name}:gpu-{time.strftime('%Y%m%d%H%M%S')}"
        print("Saving the current container...")
        if run.interactive([mgr, "commit", name, snapshot], stdout=run.DEVNULL) != 0:
            echo(f"{RED}Couldn't save the container; nothing was changed.{RESET}")
            return 1
        image = snapshot
    print("Creating the new container...")
    nvidia = ["--nvidia"] if container.has_nvidia_host() else []
    _quiet(["distrobox", "rm", "--force", new])
    hostname = run.capture(["hostname"], stderr=None)[1].rstrip("\n")
    created = run.interactive(["distrobox", "create", "-i", image, "-n", new, "--hostname", hostname, *nvidia,
                               "--no-entry", "--yes"], stdout=run.DEVNULL) == 0
    if not created or _enter("test", "-x", f"{paths.WINE_CUSTOM_BIN}/wine", name=new) != 0:
        echo(f"{RED}The new container didn't work; your current one is unchanged.{RESET}")
        _quiet(["distrobox", "rm", "--force", new])
        if snapshot:
            _quiet([mgr, "rmi", snapshot])
        return 1
    # Keep the computer's identity (Wine's system UUID, which e.g. Cantai's license is tied to)
    if len(machine_id) == 32:
        run.check(_enter("bash", "-c", "sudo mkdir -p /var/lib/dbus && sudo rm -f /var/lib/dbus/machine-id && "
                         f"echo {machine_id} | sudo tee /var/lib/dbus/machine-id >/dev/null", name=new), strict)
    _quiet(["distrobox", "stop", new, "--yes"])
    run.check(run.interactive(["distrobox", "rm", "--force", name], stdout=run.DEVNULL), strict)
    run.check(run.interactive([mgr, "rename", new, name]), strict)
    container_gpu_setup()
    # Earlier prebuilt engines, and the snapshot the old container was made from (NVIDIA conversion), are no
    # longer needed
    images = run.capture([mgr, "images", "--format", "{{.Repository}}:{{.Tag}}"])[1].split()
    for old in images:
        if old.startswith(paths.image_repo() + ":") and old != image:
            _quiet([mgr, "rmi", old])
    if current.startswith(f"localhost/{name}:gpu-") and current != image:
        run.check(_quiet([mgr, "rmi", current]), strict)
    print("Container replaced.")
    return 0


def rebuild_wine(strict=True):
    if not container.exists():
        echo(f"{RED}Error: Container '{paths.container_name()}' does not exist.{RESET}")
        print("Please install or initialize Torquio first.")
        return 1
    echo(f"{BLUE}=== Rebuilding Wine Engine ==={RESET}")
    print("This will recompile the custom Wine binary inside the container and install it to /opt/wine-custom.")
    print()
    print("Terminating any running Wine instances...")
    run.check(_enter("bash", "-c", f'export PATH="{paths.WINE_CUSTOM_BIN}:$PATH"; wineserver -k 2>/dev/null || true; '
                     "wineserver -w 2>/dev/null || true"), strict)
    prefix.apply_settings()
    print("Running build_wine.sh inside container...")
    run.check(_enter("bash", "-c", f'cd "{paths.repo_dir()}" && ./scripts/1-build/build_wine.sh --rebuild'), strict)
    print()
    echo(f"{WINE}Wine rebuild complete!{RESET}")
    return 0


def update_wine_engine(strict=True):
    """Bring the engine up to date with this copy of Torquio: download the matching prebuilt engine when there
    is one, otherwise offer to compile it."""
    image = engine.prebuilt_image()
    prefix.apply_settings()
    later = "You can update it later from Wine Tools & Maintenance > Update / Rebuild Wine Engine."
    if image:
        if container.image() == image:
            echo(f"{GREEN}Torquio's Wine engine is up to date.{RESET}")
            if ui.yes(ui.ask("Compile it from source anyway (20-40 minutes)? [y/N]: ", strict=False)):
                rebuild_wine(strict=False)
            return 0
        print("Torquio's Wine engine can be downloaded ready-made (a few minutes; Wine and Dorico are closed "
              "while the container is replaced).")
        if ui.no(ui.ask("Download it now? [Y/n]: ", strict=False)):
            print(later)
            return 0
        if container.pull_image(image):
            return run.check(replace_container(image, strict), strict)
        echo(f"{YELLOW}The prebuilt engine for this version of Torquio isn't available yet (it's published within "
             f"about an hour of each update). You can try again later, or compile it now.{RESET}")
    if ui.yes(ui.ask("Compile the Wine engine now (20-40 minutes)? [y/N]: ", strict=False)):
        return run.check(rebuild_wine(strict), strict)
    print(later)
    return 0


def setup_gpu_access(quiet=False, strict=True):
    """Make the user's GPUs available to AI plug-ins (safe to re-run). `quiet` skips the explanation when
    nothing needs the user's attention."""
    if container.has_nvidia_host() and not container.has_nvidia_libraries():
        echo(f"{BLUE}=== GPU Access for AI Plug-ins ==={RESET}")
        print("Your computer has an NVIDIA GPU that Torquio's container can't use yet. Torquio can re-create the")
        print("container with access to it (a few minutes). Dorico, your settings and your licenses aren't affected.")
        print()
        if not ui.no(ui.ask("Set up NVIDIA access now? [Y/n]: ", strict=False)):
            if replace_container(strict=False) != 0:
                return 1
    elif not quiet:
        echo(f"{BLUE}=== GPU Access for AI Plug-ins ==={RESET}")
    container_gpu_setup()
    run.interactive([os.path.join(paths.repo_dir(), "scripts/2-install/install_vkd3d_proton.sh")])
    return 0


def manage_ai_gpu(strict=True):
    run.check(setup_gpu_access(quiet=True, strict=strict), strict)
    while True:
        current = config.get_text("ai_gpu", "auto")
        gpus = container.vulkan_gpus()
        echo()
        echo(f"{BLUE}=== GPU for AI Plug-ins (e.g. Cantai) ==={RESET}")
        print("AI plug-ins run their models on this GPU (changes apply the next time Dorico starts).")
        print()
        print("GPUs found:")
        for g in gpus:
            kind = "dedicated" if "DISCRETE" in g.split("|", 1)[0] else "integrated"
            echo(f"  - {g.split('|', 1)[-1]} {GRAY}({kind}){RESET}")
        if not gpus:
            print("  (none)")
        print()
        echo(f"Current setting: {WINE}{current}{RESET}")
        echo()
        echo(f"  {WINE}1){RESET} Automatic (the strongest GPU)")
        echo(f"  {WINE}2){RESET} Choose a GPU")
        echo(f"  {WINE}3){RESET} Off (AI plug-ins use the CPU)")
        echo(f"  {WINE}4){RESET} [Back]")
        echo()
        choice = ui.ask("Select an option (1-4): ", strict=False)
        if choice == "1":
            config.set_text("ai_gpu", "auto")
        elif choice == "2":
            for i, g in enumerate(gpus, 1):
                echo(f"  {WINE}{i}){RESET} {g.split('|', 1)[-1]}")
            pick = ui.ask(f"GPU (1-{len(gpus)}): ", strict=False)
            if pick.isascii() and pick.isdigit() and 1 <= int(pick) <= len(gpus):
                config.set_text("ai_gpu", gpus[int(pick) - 1].split("|", 1)[-1])
        elif choice == "3":
            config.set_text("ai_gpu", "off")
        else:
            return 0


def fix_machine_identity(quiet=False, strict=True):
    """Containers created before Torquio derived the machine ID from the host's have one they made up. Torquio
    keeps it whenever it re-creates the container, but if the container is ever lost the new one gets the
    derived ID, and plug-ins tied to the old one (e.g. Cantai) see a new computer. Switching to the derived ID
    once, with those plug-ins deactivated, avoids that. Returns 0 or 1."""
    derived = identity.derived_machine_id()
    current = identity.container_machine_id()
    if len(derived) != 32 or len(current) != 32:
        print("Couldn't read this computer's identity; nothing was changed.")
        return 1
    if current == derived:
        if not quiet:
            echo(f"{GREEN}This computer's identity is already stable; nothing to do.{RESET}")
        return 0
    echo(f"{BLUE}=== Computer Identity ==={RESET}")
    print("Windows programs identify this computer by an ID that Torquio's container made up when it was created.")
    print("Torquio now derives it from your computer instead, so it stays the same even if the container ever has")
    print("to be created from scratch. Some plug-ins (e.g. Cantai) tie their license to this ID: changing it makes")
    print("them see a new computer, so deactivate them first and activate them again afterwards. Steinberg")
    print("licenses aren't affected. It's unlikely to ever matter, but it's worth doing once.")
    print()
    plugins = licenses.active_plugins(paths.prefix_dir())
    if plugins:
        echo(f"{YELLOW}Still activated:{RESET}")
        echo()
        for name, where in plugins:
            echo(f"{YELLOW}{name}{RESET} (deactivate it {where})")
        echo()
        print("Deactivate them, then run 'torquio --fix-identity'.")
        return 0
    if not ui.yes(ui.ask("Have you deactivated every plug-in license tied to this computer, and should Torquio "
                         "change the ID now? [y/N]: ", strict=False)):
        print("Nothing was changed. You can do this later with 'torquio --fix-identity'.")
        return 0
    print("Closing Wine (and Dorico, if it's open)...")
    run.check(_enter("bash", "-c", prefix.env_script() + "wineserver -k 2>/dev/null; wineserver -w 2>/dev/null; "
                     f"sudo rm -f /var/lib/dbus/machine-id; echo {derived} | sudo tee /var/lib/dbus/machine-id >/dev/null"),
              strict)
    if identity.container_machine_id() == derived:
        echo(f"{GREEN}Done. Activate your plug-ins again the next time you open Dorico.{RESET}")
        return 0
    print("Couldn't change the ID; nothing was changed.")
    return 1
