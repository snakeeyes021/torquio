# Design: Torquio's GUI

Status: **ready for v0.7.0 review** (`gui/`, on `feat/gui`): reviewed and fixed, tasks checked end to end in a VM; the icon waits for the maintainer.

**Who decided what.** Owner-given (the maintainer's own decisions): a graphical Torquio; it ships as
v0.7.0, without Flathub; it's built from this repository's checkout in GNOME Builder (no separate worktree,
nothing installed for previews); Flathub comes later (v0.8.0 or v0.9.0) and needs an overhaul of the
architecture below, since this design isn't Flathub-compliant (see `docs/BACKLOG.md`). Everything else in this
document (the architecture, the screens, the API, the icon, the wording) is agent-proposed and open until the
maintainer confirms it.

## Goal

A GNOME app (a Flatpak; Flathub later, see above) that does everything the `torquio` menu does, for people who'd rather not use a
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

So the app is **one thing that carries Torquio**, a "Flatpak in name only" (the maintainer, 2026-11-06): it uses
the same host pieces in the same places as the terminal Torquio, with broad permissions, and works with
existing installs (v0.8.0/0.9.0 is the real Flatpak, for Flathub):

- **Torquio is inside the app** (`/app/share/torquio/tree`, put there by `gui/bundle.py` with a stamp naming its
  version and a hash of its files). On every start, when the host's copy has a different stamp, the app places
  its own there, silently: a tar stream through `flatpak-spawn` (no filesystem permission needed), unpacked next
  to the old copy and swapped in, with the user's `installers/` folder kept. When it replaced the copy and
  Torquio is installed, it runs the `app-refresh` task: launchers, the `torquio` command, icons and the prefix's
  settings, from the new copy (what Update Torquio's refresh did). The app and the Torquio it runs are always
  the same version; there's nothing to update separately and no git.
- The GUI runs that copy's `torquio` through `flatpak-spawn --host` (Flatpak permission
  `--talk-name=org.freedesktop.Flatpak`; DistroShelf on Flathub does the same to drive distrobox). Outside
  Flatpak (development) the same calls run directly. For developing Torquio, `TORQUIO_HOST_REPO=/path/to/checkout`
  in the app's environment (e.g. GNOME Builder's run environment) makes it run that checkout instead.
- `torquio api VERB` is the GUI's interface: JSON on stdout and nothing else (no session log header, no
  colours, no prompts).
- Long tasks (install, engine download or rebuild, uninstall) print one JSON event per line
  (`{"event": "phase", ...}`, `{"event": "log", "text": ...}`, `{"event": "done", "code": 0}`), which the GUI
  shows as progress plus a log view. The GUI collects every answer first (the wizard's settings, confirmations)
  and passes them as options, so nothing waits on a terminal prompt. Where Torquio needs root (NTsync), it
  uses `pkexec` so polkit shows its own password dialog.
- What the host needs (Python 3.9+, Distrobox, Podman or Docker) is checked with the shell alone, before
  Torquio can run; the setup's "What Torquio Needs" page shows what's missing and the README's command for the
  system, and runs it (with pkexec, or for the user only) or lets the user copy it (`lib/torquio/prereqs.py`).
  Image-based systems are never changed: only Distrobox's user-level install, into `~/.local`.

**Where things live** (the same for the app and the terminal Torquio):

| What | Where |
|---|---|
| The app's copy of Torquio | `~/.local/share/torquio/app` (the installers you chose are in its `installers/`) |
| The Wine prefix (Dorico, its settings, your folder mappings) | `~/.local/share/torquio/prefix` |
| Settings | `~/.config/torquio/config.json` |
| The container | `torquio-env` (distrobox) |
| Launchers and the `torquio` command | `~/.local/bin` (they name the copy of Torquio they run) |
| Logs | `~/.local/share/torquio/logs` |

Uninstalling removes all of it except the app's copy (it may be the code doing the uninstall); with "I'm
Removing the App Too" that goes last, and otherwise the app puts it back the next time it starts. An early 0.7.0
build put the copy in `~/.local/share/torquio-app`; the app moves it on its next start.

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
  `updates [check | daily]`, `guards` (activated licenses and projects in the prefix, for the uninstall dialog).
- Tasks, `task NAME ARGS...`: `install OPTIONS_JSON`, `update`, `fix-icons`, `engine-update`,
  `engine-rebuild`, `setup-gpu`, `ntsync` (pkexec), `logs`, `wine PROGRAM`, `uninstall RESTORE`. A task runs in a
  child process with empty input and a session log; its output becomes `log` events, its steps `phase` events
  (the CLI's step headings, renamed for people), and it ends with `done` and the exit code. Only one task
  that changes the installation runs at a time (a lock; a second ends with `done` code 3, `"error": "busy"`;
  `wine` is exempt). If the GUI goes away mid-task, the task still finishes (its output then only goes to the
  session log). A data verb's stdout is only its JSON; anything the CLI helpers print goes to stderr.

## Not Flathub (yet)

This design runs as a Flatpak (built from the repository, in GNOME Builder) with
`--talk-name=org.freedesktop.Flatpak`, Wayland with X11 fallback, `--share=ipc` and `--device=dri`, and drives
the host's Torquio. That isn't Flathub-compliant: the maintainer has moved a Flathub submission to v0.8.0 or
v0.9.0, with an overhaul (`docs/BACKLOG.md`, "v0.8.0/0.9.0: Flathub-compliant architecture"). The metainfo and
its screenshots (`gui/data/screenshots/`, taken in a test VM) serve the local build and GNOME Software; the
only manifest is the local one at the repository's root.

## Existing installs

An install made with the terminal Torquio (a git checkout, its launchers) is adopted as it is: the prefix,
settings and container are where the app looks, so nothing needs pointing at. On its first start the app places
its copy and moves the launchers and the `torquio` command to it; the checkout keeps working as a developer copy
(`./torquio -f` in it points the launchers back). Nothing is wiped. The app can only miss an install moved or
renamed by hand, or one made with a custom `XDG_DATA_HOME` or `TORQUIO_CONTAINER_NAME`.

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
