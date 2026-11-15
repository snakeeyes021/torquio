"""Update Torquio (main menu, `torquio --update`), what runs after an update (`--post-update`), and Fix Icons &
Refresh Launchers."""
import glob
import os
import re

from .. import container, engine, paths, plugins, prefix, run, ui, uninstall
from ..ui import BLUE, GREEN, RED, RESET, YELLOW, echo
from . import engine as engine_cli

# update_torquio's exit code after a successful update: the caller then runs the updated copy with
# `--post-update OLD_HEAD` (Bash: exec), so whatever the update changed is used from then on
UPDATED = 100


def _git(*args):
    return ["git", "-C", paths.repo_dir(), *args]


def update_torquio(menu=False):
    """Returns 0, 1, or UPDATED. `menu`: called from the main menu (where Bash ran it with `|| true`, so set -e
    didn't apply)."""
    strict = not menu
    echo(f"{BLUE}=== Update Torquio ==={RESET}")
    echo()
    from .. import appinfo
    if appinfo.is_app_copy():
        echo(f"{YELLOW}This copy of Torquio comes with the Torquio app, which keeps it up to date.{RESET}")
        print("Update the app (in GNOME Software, or with 'flatpak update') to update Torquio.")
        return 0
    if not run.succeeds(_git("rev-parse", "--is-inside-work-tree")):
        echo(f"{RED}This copy of Torquio can't update itself (it wasn't installed with 'git clone').{RESET}")
        print("Download the latest version from https://github.com/snakeeyes021/torquio instead.")
        return 1
    if not run.succeeds(_git("rev-parse", "--abbrev-ref", "@{u}")):
        echo(f"{RED}This copy of Torquio isn't following a branch on GitHub, so it can't update itself.{RESET}")
        print(f"In {paths.repo_dir()}, switch back to the main branch ('git checkout main') and try again.")
        return 1
    print("Checking for updates...")
    if run.interactive(_git("fetch", "--quiet")) != 0:
        echo(f"{RED}Couldn't reach GitHub. Check your internet connection and try again.{RESET}")
        return 1
    code, out = run.capture(_git("rev-list", "--count", "HEAD..@{u}"), stderr=None)
    run.check(code, strict)
    count = int(out.strip() or 0)
    if count == 0:
        echo(f"{GREEN}Torquio is up to date.{RESET}")
        # It may have been updated another way (git pull), so nothing else refreshed what depends on it
        if ensure_launchers():
            print("Refreshed the launchers (they were from an older version of Torquio).")
        run.check(plugins.provision(), False)
        return 0
    changed = run.capture(_git("status", "--porcelain", "--untracked-files=no"), stderr=None)[1]
    ahead = run.capture(_git("rev-list", "--count", "@{u}..HEAD"), stderr=None)[1].strip()
    if changed.strip("\n") or ahead != "0":
        echo(f"{RED}Torquio's files have been changed on this computer, so the update can't be applied automatically.{RESET}")
        print(f"Your changes haven't been touched. In {paths.repo_dir()}, keep or discard them, then run the update again.")
        return 1
    print()
    print(f"{count} update(s) available:")
    log = run.capture(_git("log", "--format=  - %s", "HEAD..@{u}"), stderr=None)[1].splitlines()
    for line in log[:20]:
        print(line)
    if count > 20:
        print(f"  ...and {count - 20} more")
    print()
    if ui.no(ui.ask("Install now? [Y/n]: ", strict)):
        print("Update cancelled.")
        return 0
    if run.interactive(_git("merge", "--ff-only", "--quiet", "@{u}")) != 0:
        echo(f"{RED}The update couldn't be applied. Nothing was changed.{RESET}")
        return 1
    echo(f"{GREEN}Torquio updated.{RESET}")
    echo()
    return UPDATED


def post_update(old_head):
    """Runs from the freshly updated copy after an update: refresh launchers and prefix settings, and offer a
    Wine engine update when the update changed the Wine build (or the engine was already out of date)."""
    changed = run.capture(_git("diff", "--name-only", old_head, "HEAD"))[1]
    if container.exists() and os.path.isfile(os.path.join(paths.prefix_dir(), ".torquio_core_installed")):
        refresh_launchers(pause=False)
        run.check(engine_cli.setup_gpu_access(quiet=True), True)
        prefix.apply_settings()
        run.check(engine_cli.fix_machine_identity(quiet=True), True)
        run.check(plugins.provision(), False)
        # Also when the engine was already out of date (e.g. Torquio was updated with git pull, or an earlier
        # offer was declined), not only when this update changed it
        if any(line.startswith("scripts/1-build/") for line in changed.splitlines()) or engine.outdated():
            echo(f"{YELLOW}There's a newer version of Torquio's Wine engine. Until it's updated, Dorico keeps running "
                 f"on the current engine.{RESET}")
            run.check(engine_cli.update_wine_engine(), True)
    else:
        print("Torquio isn't installed yet, so there's nothing else to refresh.")
    return 0


def refresh_after_app_update():
    """After the app places a new copy of itself on the host (and on its first run over an install made from a
    git checkout): what --post-update does, from that copy, without asking anything. A newer Wine engine isn't
    downloaded here (it's large); the app offers it."""
    if container.exists() and os.path.isfile(os.path.join(paths.prefix_dir(), ".torquio_core_installed")):
        refresh_launchers(pause=False)
        run.check(engine_cli.setup_gpu_access(quiet=True), True)
        prefix.apply_settings()
        run.check(engine_cli.fix_machine_identity(quiet=True), True)
        run.check(plugins.provision(), False)
    else:
        print("Torquio isn't installed yet, so there's nothing else to refresh.")
    return 0


def refresh_launchers(pause=True):
    """Fix Icons & Refresh Launchers: icons and desktop files, prefix registry settings, and the launchers in
    ~/.local/bin."""
    repo = paths.repo_dir()
    echo(f"{BLUE}=== Refreshing Launchers & Icons ==={RESET}")
    echo()
    run.check(run.interactive(["distrobox", "enter", paths.container_name(), "--", "bash", "-c",
                               f'cd "{repo}" && ./scripts/2-install/extract_icons.sh']), True)
    # Wine's own launchers and file types for the prefix duplicate Torquio's (e.g. a second Dorico in Open With)
    uninstall.remove_menu_builder_leftovers()
    run.interactive(["update-desktop-database", os.path.join(paths.home(), ".local/share/applications/")],
                    stdout=run.DEVNULL, stderr=run.DEVNULL)
    run.interactive(["update-mime-database", os.path.join(paths.home(), ".local/share/mime/")],
                    stdout=run.DEVNULL, stderr=run.DEVNULL)
    print("Refreshing Wine prefix registry settings & debugger...")
    run.check(run.interactive(["distrobox", "enter", paths.container_name(), "--", "bash", "-c",
                               f'cd "{repo}" && ./scripts/2-install/setup_prefix.sh']), True)
    print("Copying launcher wrapper scripts to ~/.local/bin/...")
    install_launchers()
    run.check(plugins.provision(), False)
    echo(f"{GREEN}Launchers and icons successfully refreshed!{RESET}")
    echo()
    if pause:
        ui.pause("Press [Enter] to return to the main menu...")


LAUNCHERS = ("torquio-dorico", "torquio-sam", "torquio-sda-handler")
LAUNCHER_REPO = re.compile(r'^REPO = "(.*)"$', re.M)


def _launcher_text(name, repo):
    with open(os.path.join(repo, "scripts/3-runtime_handlers", name)) as f:
        return f.read().replace("@TORQUIO_REPO_DIR@", repo)


def stale_launchers():
    """The launchers in ~/.local/bin that this copy should rewrite: ones that point at this copy but differ from
    what it writes now, older launchers that don't say which copy they belong to (the Bash ones before v0.6.0),
    ones pointing at a copy that no longer exists, and missing ones. Launchers of another existing copy (e.g. the
    app's while a developer checkout runs) are left to that copy."""
    repo = paths.repo_dir()
    bindir = os.path.join(paths.home(), ".local/bin")
    stale = []
    for name in LAUNCHERS:
        try:
            with open(os.path.join(bindir, name), encoding="utf-8", errors="replace") as f:
                current = f.read()
        except OSError:
            stale.append(name)
            continue
        m = LAUNCHER_REPO.search(current)
        owner = m.group(1) if m else ""
        if owner and os.path.realpath(owner) != os.path.realpath(repo) and \
                os.path.isfile(os.path.join(owner, "torquio")):
            continue
        if current != _launcher_text(name, repo):
            stale.append(name)
    return stale


def ensure_launchers():
    """Rewrite the launchers when they're stale (e.g. Torquio's folder was updated with git pull, so "Update
    Torquio" had nothing to do and never refreshed them). Only once Torquio is installed. Returns the names
    rewritten."""
    if not os.path.isfile(os.path.join(paths.prefix_dir(), ".torquio_core_installed")):
        return []
    stale = stale_launchers()
    if stale:
        install_launchers(stale, link=not os.path.exists(os.path.join(paths.home(), ".local/bin/torquio")))
    return stale


def install_launchers(names=LAUNCHERS, link=True):
    """Copy the launchers (`names`, all by default) to ~/.local/bin, with this copy's path filled in, and (`link`)
    point the `torquio` command at this copy."""
    repo = paths.repo_dir()
    bindir = os.path.join(paths.home(), ".local/bin")
    os.makedirs(bindir, exist_ok=True)
    for name in names:
        with open(os.path.join(bindir, name), "w") as f:
            f.write(_launcher_text(name, repo))
    # The `torquio` command: this copy's (after the app places its copy, the terminal runs that one too)
    link_path = os.path.join(bindir, "torquio")
    target = os.path.join(repo, "torquio")
    if link and os.path.realpath(link_path) != os.path.realpath(target):
        if os.path.islink(link_path) or os.path.exists(link_path):
            os.remove(link_path)
        os.symlink(target, link_path)
    # Older versions copied the monitor query here too; the launchers now use the Torquio folder's own
    try:
        os.remove(os.path.join(bindir, "torquio_graphics.py"))
    except FileNotFoundError:
        pass
    umask = os.umask(0)
    os.umask(umask)
    for path in glob.glob(os.path.join(glob.escape(bindir), "torquio*")):  # chmod +x (which honours the umask)
        os.chmod(path, os.stat(path).st_mode | (0o111 & ~umask))
