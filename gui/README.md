# Torquio GUI

The graphical app for Torquio (`tech.redfoxlabs.Torquio`), for GNOME and Flathub. It drives the Torquio
installed on the host through `torquio api` (see `docs/GUI.md`).

Build and run it as a Flatpak from the repository's root:

    flatpak run org.flatpak.Builder --user --install --force-clean gui/build-dir gui/tech.redfoxlabs.Torquio.json
    flatpak run tech.redfoxlabs.Torquio

Or open `gui/` in GNOME Builder.
