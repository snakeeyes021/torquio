"""Uninstall/Wipe Torquio (main menu, `torquio --uninstall`, scripts/cleanup.sh).

Exit codes: 0 when removed, 10 when the user cancelled (the installer checks for it after running this).
The uninstaller never ran with set -e, so end of input at a prompt just counts as the answer typed so far.
"""
import os

from .. import config, graphics, licenses, paths, run, uninstall, ui
from ..ui import BLUE, GRAY, GREEN, RED, RESET, WINE, YELLOW, echo
from .graphics import cosmic_desc, gnome_desc, kde_desc

CANCELLED = 10


def ask(prompt):
    return ui.ask(prompt, strict=False)


def cancelled(message="Cleanup cancelled."):
    print(message)
    return CANCELLED


def license_guard():
    """Refuse to delete a prefix that still holds activated licenses (Steinberg's, and plug-ins Torquio can
    detect, e.g. Cantai) unless the user explicitly accepts it. Returns CANCELLED or None."""
    prefix = paths.prefix_dir()
    try:
        state = licenses.steinberg_state(prefix)
    except Exception:
        state = "unknown the license check failed to run"
    try:
        plugins = licenses.active_plugins(prefix)
    except Exception:
        plugins = []
    active, hints = [], []
    if state.startswith("active"):
        active.append(state[len("active\n"):] if state.startswith("active\n") else state)
        hints.append("Steinberg products in the Steinberg Activation Manager")
    for name, where in plugins:
        if name:
            active.append(name)
            hints.append(f"{name} {where}")
    if active:
        echo(f"⚠️  {RED}These licenses are still activated in this installation:{RESET}")
        echo()
        echo(f"{YELLOW}{chr(10).join(active)}{RESET}")
        echo()
        if state.startswith("unknown"):
            echo(f"{YELLOW}Torquio also couldn't determine whether your Steinberg licenses are deactivated "
                 f"({state[len('unknown '):] if state.startswith('unknown ') else state}).{RESET}")
            echo()
        print(f"Deactivate them ({', '.join(hints)}), then run the uninstall again. If you delete them while they're "
              "activated, you can no longer deactivate them from this computer.")
        print()
        override = "yes, I'm aware my license is active and deleting it will prevent me from ever deactivating it. proceed anyways"
        if ask(f"To uninstall anyway, type '{override}': ") != override:
            return cancelled()
    elif state.startswith("unknown"):
        echo(f"⚠️  {YELLOW}Torquio couldn't determine whether your Steinberg licenses are deactivated "
             f"({state[len('unknown '):] if state.startswith('unknown ') else state}).{RESET}")
        print("Open the Steinberg Activation Manager and make sure every product is deactivated before continuing.")
        print()
        override = "no, I promise, I've deactivated my license"
        if ask(f"To continue, type '{override}': ") != override:
            return cancelled()
    else:
        echo(f"{GREEN}No activated Steinberg or Cantai licenses found in this installation.{RESET}")
        if not ui.yes(ask("Have you deactivated every license in this installation (Steinberg products and any plug-ins)? (y/N): ")):
            return cancelled()
    return None


def project_guard():
    projects = uninstall.prefix_projects()
    prefix = paths.prefix_dir()
    if projects:
        echo(f"⚠️  {RED}Torquio found Dorico projects stored inside the Wine prefix, which will be deleted:{RESET}")
        echo()
        for project in projects[:10]:
            echo(f"{YELLOW}{project[len(prefix) + 1:] if project.startswith(prefix + '/') else project}{RESET}")
        if len(projects) > 10:
            echo(f"{YELLOW}... and {len(projects) - 10} more{RESET}")
        echo()
        print(f"Copy any you want to keep somewhere outside {prefix} first (e.g. your Documents folder).")
        print()
        override = "yes, I've saved my projects elsewhere or I'm ok with losing them"
        if ask(f"To continue, type '{override}': ") != override:
            return cancelled()
    elif not ui.yes(ask("Have you backed up any Dorico projects you were keeping in the data directory? (y/N): ")):
        return cancelled()
    return None


def restore_banner(intro_first, de, from_desc, to_desc, intro):
    echo()
    echo(f"{BLUE}================================================================{RESET}")
    echo(f"          {WINE}XWayland Global Scaling Policy Restore{RESET}")
    echo(f"{BLUE}================================================================{RESET}")
    detected = f"Torquio detected that host {de} XWayland policy was modified from {WINE}{from_desc}{RESET} to {WINE}{to_desc}{RESET}."
    if intro_first:
        echo(detected)
    for line in intro:
        print(line)
    echo(f"{BLUE}================================================================{RESET}")
    echo()
    if not intro_first:
        echo(detected)


INTRO = ["During setup/launch, you set Torquio to automatically adjust your desktop",
         "environment's global XWayland scaling policy to match the ideal",
         "setting for Dorico.",
         "",
         "Restoring this setting will return your system to its original scaling",
         "behavior (which may affect how other XWayland applications scale)."]
KDE_INTRO = ["During setup/launch, Torquio automatically adjusted your desktop",
             "environment's global XWayland scaling policy to match the ideal",
             "setting for Dorico. This ensured Dorico's interface rendered crisply",
             "at high resolution (unscaled by the compositor) instead of looking blurry.",
             "",
             "Restoring this setting will return your system to its original scaling",
             "behavior (which may affect how other XWayland applications scale)."]


def restore_scaling():
    """Offer to put back the desktop's XWayland policy that Automated Mode changed."""
    orig_scale = config.get_text("original_scale_factor", "")
    orig_kde = config.get_text("original_kde_policy", "")
    orig_cosmic = config.get_text("original_cosmic_policy", "")
    if config.get_text("manage_graphics", "false") != "true" and config.get_text("auto_scale_mutter", "false") != "true":
        return
    if orig_scale:
        current = graphics.xwayland_scaling_factor()
        if (current or "0") != orig_scale:
            from_desc = gnome_desc(orig_scale)
            restore_banner(True, "GNOME", from_desc, gnome_desc(current), INTRO)
            if not ui.no(ask(f"Would you like to restore your host display scale to {from_desc}? [Y/n]: ")):
                if run.have("gsettings"):
                    graphics.set_gnome_xwayland_factor(orig_scale)
                    echo(f"  [{GREEN}SUCCESS{RESET}] Host display scale restored to {from_desc}.")
                else:
                    echo(f"  [{YELLOW}WARNING{RESET}] gsettings not found. Manual scale restore required.")
    if orig_kde:
        current = graphics.kde_xwayland_policy() or "true"
        if current != orig_kde:
            from_desc = kde_desc(orig_kde)
            restore_banner(False, "KDE", from_desc, kde_desc(current), KDE_INTRO)
            if not ui.no(ask(f"Would you like to restore your KDE XWayland clients scale policy to {from_desc}? [Y/n]: ")):
                if run.have("kwriteconfig6") or run.have("kwriteconfig5"):
                    graphics.set_kde_xwayland_policy(orig_kde)
                    echo(f"  [{GREEN}SUCCESS{RESET}] Host KDE XWayland policy restored to {from_desc}.")
                else:
                    echo(f"  [{YELLOW}WARNING{RESET}] kwriteconfig6 or kwriteconfig5 not found. Manual scale restore required.")
    if orig_cosmic:
        current = graphics.cosmic_xwayland_policy() or "none"
        if current != orig_cosmic:
            from_desc = cosmic_desc(orig_cosmic)
            restore_banner(True, "COSMIC", from_desc, cosmic_desc(current), INTRO)
            if not ui.no(ask(f"Would you like to restore your COSMIC XWayland clients scale policy to {from_desc}? [Y/n]: ")):
                graphics.write_cosmic_policy(None if orig_cosmic == "none" else orig_cosmic)
                echo(f"  [{GREEN}SUCCESS{RESET}] Host COSMIC XWayland policy restored to {from_desc}.")


def main():
    name = paths.container_name()
    echo()
    print("This operation will permanently delete the following:")
    echo(f" - Distrobox container: {WINE}{name}{RESET}")
    echo(f" - Data directory:      {GRAY}{paths.data_dir()}{RESET} (includes Wine prefix)")
    echo(f" - Cache directory:     {GRAY}{paths.cache_dir()}{RESET} (includes Wine source code and compilation artifacts)")
    print(" - Host integration scripts and .desktop files")
    print(" - Extracted desktop icons")
    print()
    if license_guard() == CANCELLED:
        return CANCELLED
    print()
    if project_guard() == CANCELLED:
        return CANCELLED
    if ask("If you have read the above warning and would like to proceed, type 'yes, permanently delete everything' "
           "to continue: ") != "yes, permanently delete everything":
        return cancelled("Confirmation failed. Cleanup cancelled.")

    restore_scaling()

    print("Removing Distrobox container...")
    run.interactive(["distrobox", "rm", name, "--force"])
    # Downloaded prebuilt engines, and snapshots made when the container was re-created with GPU access
    for mgr in ("podman", "docker"):
        if not run.have(mgr):
            continue
        for image in uninstall.container_images(mgr):
            if run.succeeds([mgr, "rmi", image]):
                print(f"Removed container image {image}")

    print("Removing data and cache directories...")
    uninstall.remove_data()
    print("Removing host integrations...")
    uninstall.remove_integrations()
    print("Removing orphaned Windows desktop shortcuts...")
    uninstall.remove_desktop_shortcuts()

    print("Updating desktop database and icon cache...")
    home = paths.home()
    run.interactive(["update-desktop-database", os.path.join(home, ".local/share/applications/")])
    run.interactive(["update-mime-database", os.path.join(home, ".local/share/mime/")])
    if run.have("gtk-update-icon-cache"):
        run.interactive(["gtk-update-icon-cache", "-f", "-t", os.path.join(home, ".local/share/icons/hicolor/")])
    echo(f"{GREEN}Cleanup complete! The Torquio environment has been wiped.{RESET}")
    return 0
