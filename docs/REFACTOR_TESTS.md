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
