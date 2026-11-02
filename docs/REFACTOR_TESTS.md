# Python port (v0.6.0): manual test checklist

**Where to start:** the port is complete on `develop`. If you only have time for part of this, do these first:
the v0.5.0 → develop update in stage 3 (the handover every existing user goes through), a fresh install in a VM
(stage 5), launching Dorico and signing in to the Activation Manager (stage 6), and the full uninstall
(stage 4). Everything else re-checks screens that the automated comparison already matched byte for byte.

Everything here needs a human or a real system; the rest is covered automatically (unit tests, the parity
harness in `tests/parity/`, and read-only comparisons on a real install). Grows with each stage of
`docs/REFACTOR.md`; worked through once before the v0.6.0 release. "Same as before" means the same as v0.5.0
(the `main` branch).

Already checked by the developer, per stage, on the main test system (Fedora Atomic, GNOME Wayland, NVIDIA,
4K at 133%, Torquio installed with Dorico, Cantai activated): the items marked *(dev)*. Re-checking them
elsewhere (another desktop, a VM) is still useful.

## Stage 0: foundation

- [x] *(dev)* `torquio --manifest` prints the same as before and no warnings. *(VM)*
- [x] *(dev)* Export Logs (menu option, or `torquio -l`) writes a zip to Downloads with the same files as before,
      and its `system-info.txt` lists your settings, Steinberg licenses and Cantai. *(VM)*
- [x] Settings > Automatically check for updates: toggling it twice shows Off, then On, and the setting
      survives restarting Torquio. *(VM)*
- [x] Uninstall with a Steinberg license still activated: the license guard still stops you (only the license
      check moved; the full uninstall flow is tested in stage 4). *(VM)*
- [x] On a system whose `python3` is older than 3.9 (e.g. openSUSE Leap 15 or Rocky/Alma 8 in a VM, if handy):
      `./torquio` prints "Torquio needs Python 3.9 or newer (yours is 3.6); install a newer python3 package."
      and stops. *(checked in a `python:3.6` container)*

## Stage 1: read-only screens

- [ ] *(dev)* Main menu header (logo and colours) looks the same; with the clock in sync there's no clock
      warning; with the network off the "could not be verified" warning appears.
- [x] *(dev)* Status Dashboard (`torquio -s`) shows the same as before on an installed system. *(VM)*
- [x] Status Dashboard on another desktop (KDE Plasma and/or COSMIC, X11 if available): desktop name, monitor,
      scale and XWayland policy lines look right. *(KDE Plasma 6 Wayland VM, at 100%, 125% and 200%: KDE always
      read as 100% until 175d026 (kscreen-doctor colours its output), fixed. COSMIC and X11 not checked.)*
- [x] Status Dashboard before installing (fresh VM): container "Not Created", prefix "Not Initialized", GPU
      section "Container not created". *(VM)*
- [x] *(dev)* Configure Graphics & Scaling (`torquio -g`): the status block at the top is the same as before
      (the options below it are still the Bash version until stage 2). *(VM)*
- [x] `torquio --no-such-flag` prints the error and the flag list. *(VM)*

## Stage 2: maintenance tools

- [x] Configure Graphics > Auto Manage Graphics: switch to Automated Mode (the warning has its green lines now)
      and back to Manual Mode; when asked, restore the XWayland setting; check GNOME Settings (or KDE/COSMIC)
      shows the original scaling behaviour again. *(VM)*
- [x] Configure Graphics > Set/change WINE Prefix DPI (Manual Mode): an invalid value, the current value
      ("already set"), and a new value (Dorico/Wine windows close; the next Dorico start uses the new DPI). Set
      it back afterwards. *(VM)*
- [x] Configure Graphics > FreeType Hinting Interpreter: switch to v35 and back to v40. *(VM)*
- [x] Configure Graphics > Match Hardware Physical DPI: enable, disable. *(VM)*
- [x] Folder mappings: map a folder as a drive letter, map the same folder again (warning, now without "033[0m"),
      map one as a Desktop shortcut, unmap each; check the drive letter appears in Dorico's file dialogs after a
      Wine server shutdown. *(VM; the drive letter was checked in a Wine file listing, not Dorico's dialog)*
- [x] `torquio -d ~/Music drive` maps from the command line. *(VM)*
- [x] *(dev)* Key commands > Export: the zip in Downloads is the same as before. *(VM)*
- [x] Key commands > Import that zip; launch Dorico; the key commands are applied. *(VM: the file was restored byte
      for byte; not checked in Dorico's preferences)*
- [x] Wine Tools > Run Custom Installer/Executable: pick a small .exe or .msi in the file picker; it runs. *(VM:
      Fedora Workstation has no zenity/kdialog, so it asked for a path instead of a picker)*
- [x] Wine Tools > Enable Kernel Fast Sync on a system without ntsync loaded (or check the message where it's
      already active). *(VM: the already-active message)*
- [ ] *(dev)* Settings, Configure Graphics, Folder Mappings and Key Commands menus look the same as before.
- [x] Ctrl+C at any prompt in those menus ends Torquio quietly (no Python traceback). *(VM)*

## Stage 3: engine, container, updates

The most important test of the release: **updating from v0.5.0 to the new version** (the handover between the
old updater and the new code). On a system with v0.5.0 installed and working (a VM is fine):

1. In the Torquio folder: `git fetch origin && git checkout -B test-update v0.5.0-alpha && git branch -u origin/develop`
   (a branch at v0.5.0 that follows develop, so "Update Torquio" offers the new version).
2. `torquio`, choose Update Torquio, install. Expected: the list of changes, "Torquio updated.", then the new
   copy takes over (launchers and icons refreshed, GPU access checked), and "Press [Enter] to return to the
   main menu..." leads to the menu of the new version.
3. Launch Dorico; Cantai (if activated) is still activated.
4. Afterwards `git checkout main` (or `develop`) to leave the test branch.

- [x] Update from v0.5.0 as above (menu), and once more with `torquio -u` from the command line. *(VM; Dorico and
      Cantai stayed activated)*
- [x] Update Torquio when it's already up to date: "Torquio is up to date." *(VM)*
- [x] Wine Tools > Update / Rebuild Wine Engine with the engine up to date: offers compiling anyway; say no. *(VM)*
- [ ] Wine Tools > Update / Rebuild Wine Engine with an older prebuilt engine (e.g. right after step 2 above if
      the engine changed since v0.5.0): downloads it, replaces the container, Dorico still starts, Cantai still
      activated. *(Not applicable to v0.5.0 → v0.6.0: the engine image is the same, `build-f568ffd9a7fc`.)*
- [x] `torquio --rebuild-wine` (20-40 minutes; only if you have the time): completes, Dorico starts. *(VM: 35
      minutes; Dorico starts)*
- [ ] On a computer with an NVIDIA GPU whose container predates NVIDIA support: `torquio --setup-gpu` offers
      to set up NVIDIA access and re-creates the container; the dashboard then shows "NVIDIA Access: Enabled".
- [ ] Wine Tools > GPU for AI Plug-ins: lists your GPUs; choose one, then Automatic, then Off, then Automatic; the
      dashboard's Setting line follows. *(VM: Off and Automatic switch and the dashboard follows; the VM has no
      GPU, so choosing one is left for the host.)*
- [x] *(dev)* `torquio --fix-identity` with a stable identity: "already stable; nothing to do." *(VM)*
- [x] Wine Tools > winecfg, regedit, control, explorer, cmd each open; Reboot Wine Prefix and Shutdown Wine
      Server finish; Open C: Drive opens the file manager; xev offers to install itself (say no). *(VM)*
- [ ] *(dev)* The Wine Tools menu looks the same as before.
- [x] Fix Icons & Refresh Launchers (main menu 5): finishes; Dorico's menu entry and file associations work. *(VM)*

## Stage 4: uninstall

Destructive: use a VM or a system where you're ready to reinstall (stage 5's tests reinstall anyway).

- [x] *(dev)* With licenses activated (Steinberg and Cantai): the guard lists them and cancels unless the long
      sentence is typed; nothing is deleted. *(VM)*
- [x] With every license deactivated and a Dorico project saved inside the prefix (e.g. in the prefix's
      `drive_c/users/<you>/Documents` if it's a real folder there): the project is listed and the uninstall
      stops unless confirmed. *(VM)*
- [x] Full uninstall (`torquio -r`, typing the confirmations): afterwards there's no `torquio-env` container
      (`distrobox list`), no `~/.local/share/torquio`, `~/.cache/torquio` or `~/.config/torquio`, no Dorico /
      Activation Manager / Download Assistant menu entries, no Torquio icons, and `.dorico` files no longer open
      with Dorico. Other Wine programs' menu entries and your other default applications are untouched. *(VM;
      Wine's own icons for the prefix are left behind, as in v0.5.0)*
- [x] With Automated Mode on before uninstalling: it offers to restore the desktop's XWayland setting (with
      blue rules around the explanation now), and restores it. *(VM)*
- [x] Uninstall from the main menu, cancelled: "Press [Enter] to return to the main menu..." and the menu again.
      *(VM)*

## Stage 5: install

- [x] Fresh install in a VM (Fedora Workstation and/or Silverblue; KDE too if possible), with the MediaBay and
      Download Assistant installers in ~/Downloads: the wizard's four steps, the manifest, the prebuilt engine
      download, then the Download Assistant opens. Install Dorico through it; the menu entry, icons and
      `.dorico` file association appear; Dorico starts. *(VM: Fedora Workstation)*
- [x] The wizard's folder mapping (drive and Desktop shortcut) and key command import (from a backup made in stage
      2) take effect after the install. *(VM: the drive in the v0.5.0 wizard, the Desktop shortcut and the key
      commands in v0.6.0's)*
- [x] With Cantai's installer in ~/Downloads: Cantai is installed and its playback template appears in Dorico.
      *(VM)*
- [ ] Re-running the installer on a complete install: each option of the "existing installation" menu (Configure
      Settings Only; Re-run Windows Software Installers; Recreate Distrobox Container Only — Cantai stays
      activated; Fresh Reinstallation — goes through the uninstaller's guards; Cancel). *(VM: every option works;
      Cantai wasn't activated there, so "Cantai stays activated" is left for the host.)*
- [x] `torquio -i -y` (automatic install with default settings). *(VM: fresh, 25 minutes, only the sudo prompt
      for NTsync)*
- [x] Without the mandatory installers: the error names the missing ones and nothing is changed. *(VM; NTsync and
      the settings file are written before the check, as in v0.5.0)*

## Stage 6: launchers

After updating (or Fix Icons & Refresh Launchers), `~/.local/bin/torquio-dorico`, `torquio-sam` and
`torquio-sda-handler` are short Python files that name your Torquio folder.

- [ ] Start Dorico from the application menu; it opens as before. Open a `.dorico` file from the file manager;
      Dorico opens it. *(VM: from the menu yes; opening a `.dorico` file from the file manager not checked yet.)*
- [x] Automated Mode on: change the display scale (e.g. 100% → 125%), start Dorico; the first time it asks to
      change the XWayland setting; Dorico's UI size follows. With Dorico already running and the scale changed,
      starting it again asks whether to restart Wine. *(VM, with zenity installed: without it there's no dialog and
      Wine restarts without asking, as in v0.5.0. Enabling Automated Mode from the menu counts as having seen the
      XWayland question, so it only appears when the wizard enabled it.)*
- [x] Activation Manager from the menu; sign in through the web login: the browser's "open link" returns to the
      Activation Manager, which signs in. *(VM)*
- [x] Download Assistant from the menu; sign in through the web login likewise. Install something small (or
      Dorico on a fresh install): the Windows shortcuts that installers put on the desktop disappear, and after
      installing Dorico its icon appears in the menu. *(VM)*
- [x] Set the system clock off by an hour and open the Activation Manager: a warning dialog appears (set the
      clock back afterwards). *(VM; the warning opens behind the Activation Manager)*
- [ ] With Cantai installed: start Dorico, play a Cantai part; rendering works (GPU if available).
- [x] Logs: each launch writes `~/.local/share/torquio/logs/torquio_dorico_*.log` (or `_sam_`, `_sda_`) with the
      same content as before. *(VM)*

## Stage 7: entry point (`torquio` is now Python)

- [x] `torquio` (menu), `./torquio` from the folder, and `~/.local/bin/torquio` all start; the menu, colours and
      header look as before; Exit, Ctrl+C at the menu prompt (ends quietly, no traceback) and Ctrl+D. *(VM)*
- [ ] Every main-menu option once (installed and not installed), returning to the menu each time.
- [x] Flags: `-s`, `-g`, `-l`, `--manifest`, `-x`, `-m`, `-w`, `-k`, `-b`, `-e some.exe`, `-d ~/Music drive`,
      `-f`, `--fix-identity`, `--setup-gpu`, `--enable-ntsync`, an unknown flag (flag list, exit code 1). *(VM)*
- [x] `~/.local/share/torquio/logs/torquio_main_*.log` records each session as before. *(VM)*
- [x] Update from v0.5.0 once more (stage 3's steps) now that the entry point is Python: the handover runs the
      new `torquio --post-update`. *(VM)*
- [x] On a system with an old Python (if handy): the "needs Python 3.9 or newer" message.
 *(checked in a `python:3.6` container)*