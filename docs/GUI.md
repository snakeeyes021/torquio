# Design: Torquio's GUI

Status: **first full version** (`gui/`, on `feat/gui`), for v0.7.0 (the GUI release).

## Goal

A GNOME app on Flathub that does everything the `torquio` menu does, for people who'd rather not use a
terminal: install, launch, settings, updates, maintenance, uninstall. The command line stays, and both use the
same core (`lib/torquio`), so behaviour can't drift apart.

## Where it lives

In this repository, in `gui/`: made from the GNOME Builder template (Python, GTK 4, libadwaita, GNOME 50
runtime), built by a `meson.build` and the Flatpak manifest `tech.redfoxlabs.Torquio.json` at the repository's
root. The app ID is `tech.redfoxlabs.Torquio`, matching Pianola and Thirties. Keeping it in the same repository
means one version and one release for the core and both interfaces; a change to the core and the screen that
uses it land together.

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

## API

`torquio api VERB` (`lib/torquio/api.py`), JSON only:

- Data: `version`, `status`, `running` (is Dorico or a Steinberg program open), `settings [set KEY VALUE]`
  (validated; graphics settings are applied at once, which restarts Wine), `display [restore]`,
  `folders [map PATH drive|desktop | unmap ...]`, `keycommands [export | import PATH]`, `gpus`, `prereqs`,
  `updates [check]`, `guards` (activated licenses and projects in the prefix, for the uninstall dialog).
- Tasks, `task NAME ARGS...`: `install OPTIONS_JSON`, `update`, `fix-icons`, `engine-update`,
  `engine-rebuild`, `setup-gpu`, `ntsync` (pkexec), `logs`, `wine PROGRAM`, `uninstall RESTORE`. A task runs in a
  child process with empty input and a session log; its output becomes `log` events, its steps `phase` events
  (the CLI's step headings, renamed for people), and it ends with `done` and the exit code.

## Flathub

Permissions: `--talk-name=org.freedesktop.Flatpak` (essential, explained in the submission), Wayland with
X11 fallback, `--share=ipc`, `--device=dri`. No network or filesystem access is needed in the sandbox: the
host does the downloading and the file work. Nothing from Steinberg is bundled.

## What's in this version

- **Setup assistant** (until Torquio is installed): welcome; when there's no Torquio on the computer at all, it
  downloads it from GitHub (to `~/.local/share/torquio-app`); what's needed (Distrobox, Podman or Docker, the
  installers, with links to their download pages and a file chooser for ones saved elsewhere); a few choices
  (scaling, font smoothing, kernel fast sync, a folder for scores, key commands found in Downloads); the install
  with its steps; done.
- **Overview:** Start Dorico (or Get Dorico, until it's installed), the Activation Manager and the Download
  Assistant; the Wine engine (with Update when there's a newer one), the container, kernel fast sync (Enable),
  playback plug-ins.
- **Display & Scaling:** Automated or Manual Mode (with the explanation, and the offer to restore the desktop's
  XWayland setting when switching off), Wine DPI (applied a moment after the last change), physical DPI, font
  smoothing, and what Torquio sees of the display.
- **Folders:** drives and Desktop shortcuts, added through the folder portal (its host path from the Documents
  portal), removed with an Undo toast.
- **Key Commands:** export to Downloads (with Show), import from Downloads or a chosen file.
- **AI Plug-ins:** the GPU AI plug-ins render on, NVIDIA access (Set Up), engine support, vkd3d-proton, Cantai.
- **Maintenance:** Wine's tools, running a Windows program, drive C:, restarting or closing Wine (asking first when
  Dorico is open), Fix Icons & Launchers, the Wine engine (Update, Rebuild), kernel fast sync, Export Logs, and
  Uninstall (the license and project checks, restoring the scaling setting, a typed confirmation).
- **Everywhere:** an update banner with what's new and Update; toasts rather than dialogs for finished actions;
  progress dialogs for long tasks (closing one lets the task carry on); Preferences (update checks, which copy of
  Torquio it talks to); keyboard shortcuts (Ctrl+Return starts Dorico, Ctrl+R refreshes); About with credits.
- For working on the setup assistant on an installed system: `TORQUIO_GUI_SETUP=1`.

## Building and running it in GNOME Builder

1. In GNOME Builder, open the repository (`~/dev/torquio`).
2. Check out the GUI's branch (`feat/gui`), in Builder or with `git checkout`.
3. Press **Run** (or Build). Builder uses `tech.redfoxlabs.Torquio.json` (GNOME 50 SDK), builds the working
   tree and runs the app in its sandbox, where it talks to the Torquio on the host (`~/.local/bin/torquio`).

Your Torquio runs from this same checkout, so checking out a branch also changes what your launchers
(`torquio`, Dorico's, the Activation Manager's, the Download Assistant's) run until you switch back. Builder
doesn't install the app.

From a terminal instead (also without installing), in the repository:

    flatpak run org.flatpak.Builder --force-clean build-dir tech.redfoxlabs.Torquio.json
    flatpak build --talk-name=org.freedesktop.Flatpak --share=ipc --socket=wayland --socket=fallback-x11 --device=dri build-dir torquio-gui
