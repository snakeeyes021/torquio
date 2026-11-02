# Design: Torquio's GUI

Status: **design and scaffold** (`gui/`, on `feat/gui-scaffold`), for v0.7.0 (the GUI release).

## Goal

A GNOME app on Flathub that does everything the `torquio` menu does, for people who'd rather not use a
terminal: install, launch, settings, updates, maintenance, uninstall. The command line stays, and both use the
same core (`lib/torquio`), so behaviour can't drift apart.

## Where it lives

In this repository, in `gui/`: a Meson project made from the GNOME Builder template (Python, GTK 4,
libadwaita, GNOME 50 runtime), with its Flatpak manifest `gui/tech.redfoxlabs.Torquio.json`. The app ID is
`tech.redfoxlabs.Torquio`, matching Pianola and Thirties. Keeping it in the same repository means one version
and one release for the core and both interfaces; a change to the core and the screen that uses it land
together.

## How a sandboxed app drives Torquio

Everything Torquio does happens on the host: distrobox and podman, the container, the Wine prefix in
`~/.local/share/torquio`, the launchers in `~/.local/bin`, desktop files, GNOME/KDE/COSMIC scaling settings,
`sudo modprobe ntsync`. The container's scripts also run from the host copy of Torquio
(`distrobox enter -- bash -c 'cd REPO && ./scripts/...'`), and the launchers name that copy. A Flatpak can't do
any of this from inside its sandbox, and its own files (`/app`) aren't visible to the host or the container.

So **the host keeps one copy of Torquio** (the git checkout it has today, updated by Update Torquio), and the
**GUI is a front end to it**:

- The GUI runs the host's `torquio` through `flatpak-spawn --host` (Flatpak permission
  `--talk-name=org.freedesktop.Flatpak`; DistroShelf on Flathub does the same to drive distrobox, and Thirties
  uses it too). Outside Flatpak (development) the same calls run directly.
- `torquio api VERB` is the GUI's interface: JSON on stdout and nothing else (no session log header, no
  colours, no prompts). `torquio api version` returns `{"api": N, "torquio": "<git describe>", ...}`; the GUI
  needs a minimum `api` and otherwise offers Update Torquio.
- Long tasks (install, update, engine download or rebuild, uninstall) print one JSON event per line
  (`{"event": "phase", ...}`, `{"event": "log", "text": ...}`, `{"event": "done", "code": 0}`), which the GUI
  shows as progress plus a log view. The GUI collects every answer first (the wizard's settings, confirmations)
  and passes them as options, so nothing waits on a terminal prompt. Where Torquio needs root (NTsync), it
  uses `pkexec` so polkit shows its own password dialog.
- First run without Torquio on the host: the GUI checks the prerequisites (git, Python 3.9+, distrobox,
  podman or docker) on the host, explains how to install missing ones for the user's distro (as the README
  does), then clones Torquio on the host and continues with the setup assistant.

Rejected: running the core inside the sandbox (it needs the host's programs and files, and the container's
scripts and launchers need a host copy anyway), and a separate host helper service over D-Bus (more to
install and keep running than `flatpak-spawn`, for no gain over a command-line interface that already exists).

## Screens

- **Setup assistant** (no install yet): prerequisites → installers (found in `~/Downloads`, or chosen through
  the file portal) → scaling, font smoothing, folder mapping, key commands → confirmation → progress → "Sign
  in to the Download Assistant to install Dorico".
- **Main window**, a sidebar (`AdwNavigationSplitView`) with:
  - **Overview:** the dashboard (container, engine, prefix, NTsync, GPU), buttons to start Dorico, the
    Activation Manager and the Download Assistant, and a banner when an update is available.
  - **Display & Scaling:** Automated or Manual Mode, Wine DPI, matching physical DPI, font smoothing.
  - **Folders:** mapped folders, add (folder portal) and remove.
  - **Key Commands:** import and export.
  - **AI Plug-ins:** the GPU chooser and Cantai's status.
  - **Maintenance:** Wine Tools (winecfg, regedit, ...), Fix Icons & Refresh Launchers, engine update and
    rebuild, NTsync, Export Logs.
  - **Preferences** (app menu): automatic update checks.
  - **Uninstall** (Maintenance, at the bottom): the license and project checks as dialogs, then a typed
    confirmation, as in the terminal.
- **Task view:** phases and a scrolling log for long tasks; closing it doesn't stop the task.

## API, in the order the screens need it

1. `version`, `status` (in the scaffold).
2. `settings get|set`, `launch dorico|sam|sda`.
3. `folders list|map|unmap`, `keycommands import|export`, `gpu list|set`.
4. `update check|apply`, `engine update|rebuild`, `fix-icons`, `ntsync enable`, `logs export`.
5. `install` (all wizard answers as options, JSON events), `uninstall` (`guards` reports licenses and
   projects; the actual uninstall takes the confirmation).

## Flathub

Permissions: `--talk-name=org.freedesktop.Flatpak` (essential, explained in the submission), Wayland with
X11 fallback, `--share=ipc`, `--device=dri`. No network or filesystem access is needed in the sandbox: the
host does the downloading and the file work. Nothing from Steinberg is bundled.

## Scaffold (this branch)

- `gui/`: the template's structure, renamed (`tech.redfoxlabs.Torquio`, module `torquio_gui`), with a
  window showing the Overview from `torquio api status` and buttons to start Dorico and Steinberg's tools, and
  `host.py`, the `flatpak-spawn --host` bridge.
- At the repository's root, only for the GUI: `meson.build` (which builds `gui/`) and the Flatpak manifest
  `tech.redfoxlabs.Torquio.json`. The manifest builds the checkout itself (`"type": "dir", "path": "."`), so a
  build always matches the checked-out branch, never a pinned commit or an installed copy.
- `lib/torquio/api.py`: `torquio api version` and `torquio api status` (also on `develop`, so the GUI can
  talk to a Torquio on `develop`).

## Building and running it in GNOME Builder

1. In GNOME Builder, open the repository (`~/dev/torquio`).
2. Check out the GUI's branch (`feat/gui-scaffold`), in Builder or with `git checkout`.
3. Press **Run** (or Build). Builder uses `tech.redfoxlabs.Torquio.json` (GNOME 50 SDK), builds the working
   tree and runs the app in its sandbox, where it talks to the Torquio on the host (`~/.local/bin/torquio`).

Your Torquio runs from this same checkout, so checking out a branch also changes what your launchers
(`torquio`, Dorico's, the Activation Manager's, the Download Assistant's) run until you switch back. Builder
doesn't install the app.

From a terminal instead (also without installing), in the repository:

    flatpak run org.flatpak.Builder --force-clean build-dir tech.redfoxlabs.Torquio.json
    flatpak build --talk-name=org.freedesktop.Flatpak --share=ipc --socket=wayland --socket=fallback-x11 --device=dri build-dir torquio-gui
