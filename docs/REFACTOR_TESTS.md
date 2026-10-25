# Python port (v0.6.0): manual test checklist

Everything here needs a human or a real system; the rest is covered automatically (unit tests, the parity
harness in `tests/parity/`, and read-only comparisons on a real install). Grows with each stage of
`docs/REFACTOR.md`; worked through once before the v0.6.0 release. "Same as before" means the same as v0.5.0
(the `main` branch).

Already checked by the developer, per stage, on the main test system (Fedora Atomic, GNOME Wayland, NVIDIA,
4K at 133%, Torquio installed with Dorico, Cantai activated): the items marked *(dev)*. Re-checking them
elsewhere (another desktop, a VM) is still useful.

## Stage 0: foundation

- [ ] *(dev)* `torquio --manifest` prints the same as before and no warnings.
- [ ] *(dev)* Export Logs (menu option, or `torquio -l`) writes a zip to Downloads with the same files as before,
      and its `system-info.txt` lists your settings, Steinberg licenses and Cantai.
- [ ] Settings > Automatically check for updates: toggling it twice shows Off, then On, and the setting
      survives restarting Torquio.
- [ ] Uninstall with a Steinberg license still activated: the license guard still stops you (only the license
      check moved; the full uninstall flow is tested in stage 4).
- [ ] On a system whose `python3` is older than 3.9 (e.g. openSUSE Leap 15 or Rocky/Alma 8 in a VM, if handy):
      `./torquio` prints "Torquio needs Python 3.9 or newer (yours is 3.6); install a newer python3 package."
      and stops.

## Stage 1: read-only screens

- [ ] *(dev)* Main menu header (logo and colours) looks the same; with the clock in sync there's no clock
      warning; with the network off the "could not be verified" warning appears.
- [ ] *(dev)* Status Dashboard (`torquio -s`) shows the same as before on an installed system.
- [ ] Status Dashboard on another desktop (KDE Plasma and/or COSMIC, X11 if available): desktop name, monitor,
      scale and XWayland policy lines look right.
- [ ] Status Dashboard before installing (fresh VM): container "Not Created", prefix "Not Initialized", GPU
      section "Container not created".
- [ ] *(dev)* Configure Graphics & Scaling (`torquio -g`): the status block at the top is the same as before
      (the options below it are still the Bash version until stage 2).
- [ ] `torquio --no-such-flag` prints the error and the flag list.

## Stage 2: maintenance tools

- [ ] Configure Graphics > Auto Manage Graphics: switch to Automated Mode (the warning has its green lines now)
      and back to Manual Mode; when asked, restore the XWayland setting; check GNOME Settings (or KDE/COSMIC)
      shows the original scaling behaviour again.
- [ ] Configure Graphics > Set/change WINE Prefix DPI (Manual Mode): an invalid value, the current value
      ("already set"), and a new value (Dorico/Wine windows close; the next Dorico start uses the new DPI). Set
      it back afterwards.
- [ ] Configure Graphics > FreeType Hinting Interpreter: switch to v35 and back to v40.
- [ ] Configure Graphics > Match Hardware Physical DPI: enable, disable.
- [ ] Folder mappings: map a folder as a drive letter, map the same folder again (warning, now without
      "033[0m"), map one as a Desktop shortcut, unmap each; check the drive letter appears in Dorico's file
      dialogs after a Wine server shutdown.
- [ ] `torquio -d ~/Music drive` maps from the command line.
- [ ] *(dev)* Key commands > Export: the zip in Downloads is the same as before.
- [ ] Key commands > Import that zip; launch Dorico; the key commands are applied.
- [ ] Wine Tools > Run Custom Installer/Executable: pick a small .exe or .msi in the file picker; it runs.
- [ ] Wine Tools > Enable Kernel Fast Sync on a system without ntsync loaded (or check the message where it's
      already active).
- [ ] *(dev)* Settings, Configure Graphics, Folder Mappings and Key Commands menus look the same as before.
- [ ] Ctrl+C at any prompt in those menus ends Torquio quietly (no Python traceback).

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

- [ ] Update from v0.5.0 as above (menu), and once more with `torquio -u` from the command line.
- [ ] Update Torquio when it's already up to date: "Torquio is up to date."
- [ ] Wine Tools > Update / Rebuild Wine Engine with the engine up to date: offers compiling anyway; say no.
- [ ] Wine Tools > Update / Rebuild Wine Engine with an older prebuilt engine (e.g. right after step 2 above if
      the engine changed since v0.5.0): downloads it, replaces the container, Dorico still starts, Cantai still
      activated.
- [ ] `torquio --rebuild-wine` (20-40 minutes; only if you have the time): completes, Dorico starts.
- [ ] On a computer with an NVIDIA GPU whose container predates NVIDIA support: `torquio --setup-gpu` offers
      to set up NVIDIA access and re-creates the container; the dashboard then shows "NVIDIA Access: Enabled".
- [ ] Wine Tools > GPU for AI Plug-ins: lists your GPUs; choose one, then Automatic, then Off, then Automatic;
      the dashboard's Setting line follows.
- [ ] *(dev)* `torquio --fix-identity` with a stable identity: "already stable; nothing to do."
- [ ] Wine Tools > winecfg, regedit, control, explorer, cmd each open; Reboot Wine Prefix and Shutdown Wine
      Server finish; Open C: Drive opens the file manager; xev offers to install itself (say no).
- [ ] *(dev)* The Wine Tools menu looks the same as before.
- [ ] Fix Icons & Refresh Launchers (main menu 5): finishes; Dorico's menu entry and file associations work.

## Stage 4: uninstall

Destructive: use a VM or a system where you're ready to reinstall (stage 5's tests reinstall anyway).

- [ ] *(dev)* With licenses activated (Steinberg and Cantai): the guard lists them and cancels unless the long
      sentence is typed; nothing is deleted.
- [ ] With every license deactivated and a Dorico project saved inside the prefix (e.g. in the prefix's
      `drive_c/users/<you>/Documents` if it's a real folder there): the project is listed and the uninstall
      stops unless confirmed.
- [ ] Full uninstall (`torquio -r`, typing the confirmations): afterwards there's no `torquio-env` container
      (`distrobox list`), no `~/.local/share/torquio`, `~/.cache/torquio` or `~/.config/torquio`, no Dorico /
      Activation Manager / Download Assistant menu entries, no Torquio icons, and `.dorico` files no longer open
      with Dorico. Other Wine programs' menu entries and your other default applications are untouched.
- [ ] With Automated Mode on before uninstalling: it offers to restore the desktop's XWayland setting (with
      blue rules around the explanation now), and restores it.
- [ ] Uninstall from the main menu, cancelled: "Press [Enter] to return to the main menu..." and the menu again.
