# Torquio GUI

The graphical app for Torquio (`tech.redfoxlabs.Torquio`), for GNOME and Flathub. It drives the Torquio
installed on the host through `torquio api` (see `docs/GUI.md`).

In GNOME Builder: open this folder (`gui/`, not the repository's root) and press Run. Builder uses
`tech.redfoxlabs.Torquio.json`, which builds this folder's working tree. Keep it in its own worktree
(`git worktree add ~/dev/torquio-gui feat/gui-scaffold`), so the checkout your Torquio runs from stays on its
branch. More in `docs/GUI.md`.
