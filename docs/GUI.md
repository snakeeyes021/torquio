# Design: Torquio's GUI

Status: **design and scaffold** (`gui/`, on `feat/gui-scaffold`). Whether it ships in v0.7.0 or the release
after is still to be decided.

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
  window showing the Overview from `torquio api status` and a Start Dorico button, and `host.py`, the
  `flatpak-spawn --host` bridge.
- `lib/torquio/api.py`: `torquio api version` and `torquio api status`.
- Build and run: `flatpak run org.flatpak.Builder --user --install --force-clean build-dir
  gui/tech.redfoxlabs.Torquio.json`, then `flatpak run tech.redfoxlabs.Torquio`.
