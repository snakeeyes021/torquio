# Torquio GUI

The graphical app for Torquio (`tech.redfoxlabs.Torquio`), for GNOME (a Flatpak built from this repository; not on Flathub, see `docs/BACKLOG.md`). It drives the Torquio
installed on the host through `torquio api` (see `docs/GUI.md`).

In GNOME Builder: open the repository, check out the GUI's branch and press Run. Builder uses
`tech.redfoxlabs.Torquio.json` at the repository's root, which builds the working tree. Checking out a branch
also changes what your Torquio launchers run, as they run this checkout.
