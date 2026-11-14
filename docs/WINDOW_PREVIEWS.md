# Black window previews on other workspaces

Status: **cause found (2026-11-14); fix planned for a release after v0.7.0.** The recommended fix (option 1) is not
built yet.

## What happens

In GNOME, the previews of Dorico's and other Wine programs' windows (the Activities overview and its workspace
thumbnails, the window switcher, dock previews) are black when the window is on a workspace other than the current
one. The title bar, which GNOME draws, is still there; the window's content is black. On the current workspace the
previews are fine. KDE and other desktops haven't been checked yet.

## Cause

It isn't the renderer. It's how Wine reads the window manager's "iconic" state.

1. **GNOME marks a window on another workspace as iconic.** For an X11 window (Wine's windows run through
   XWayland), Mutter sets `WM_STATE` to `IconicState` when the window's workspace isn't shown. It does the same
   when the window is minimized, but then it also sets `_NET_WM_STATE_HIDDEN`. On another workspace that flag
   isn't set:

   | Window | `WM_STATE` | `_NET_WM_STATE` |
   |---|---|---|
   | Shown | Normal | (focused) |
   | On another workspace | Iconic | no `_NET_WM_STATE_HIDDEN` |
   | Minimized | Iconic | `_NET_WM_STATE_HIDDEN` |

2. **Wine treats every iconic window as minimized.** Wine's X11 driver (`window_update_client_state` in
   `dlls/winex11.drv/window.c`) minimizes the Windows window whenever the X11 window turns iconic, if the
   window has a minimize box. With Wine's X11 tracing on, moving the window to another workspace logs
   `minimizing win ...`. The Windows program believes it was minimized and stops drawing, so the last frame
   GNOME has for the preview is black.

That explains the pattern:

- **Windows with a minimize box go black:** the Activation Manager and Dorico.
- **Windows without one keep their previews:** for example, Wine's own configuration dialog.
- **Native X11 programs aren't affected:** they don't react to the iconic state.

Upstream Wine (master, November 2026) behaves the same way. There's no open upstream report for this case. Related
ones:
- **Wine bug 10142 (2010):** some window managers minimize windows on a desktop switch. The suggestion there was
  that telling the two apart is a window manager standards (freedesktop.org) question; `_NET_WM_STATE_HIDDEN` is
  that standard signal.
- **Wine bug 45690:** window managers whose iconic state means something else.

**How it was checked:**

- **Machine:** a test machine with Fedora 44 and GNOME 50, Torquio's Wine 11.5 engine, in a test prefix.
- **Test program:** the Steinberg Activation Manager. It uses the same stack as Dorico: Qt 6 Quick on Direct3D 11
  and DirectComposition, through wined3d.
- **Renderer variants, all black:**
  - wined3d on Vulkan (the default);
  - wined3d on OpenGL (`WINE_D3D_CONFIG=renderer=gl`);
  - Qt Quick on OpenGL (`QSG_RHI_BACKEND=opengl`);
  - Qt Quick's software renderer (`QT_QUICK_BACKEND=software`).
- **Kept their previews:** a Wine virtual desktop, and Wine's Wayland driver.

A side effect beyond the previews: while its window is on another workspace, the program is minimized as far as
Windows is concerned. Programs that change what they do when minimized will behave that way there. This wasn't
tested with Dorico's playback.

## Fix options

| | Option | Previews | Cost | Risk |
|---|---|---|---|---|
| 1 | **Wine patch: treat "iconic" as minimized only when the window manager also says hidden.** In `winex11.drv`, read `_NET_WM_STATE_HIDDEN`. When the window manager supports it (it's in `_NET_SUPPORTED`) and an iconic window doesn't have it, the window is on another workspace: don't minimize the Windows window, and don't ask the window manager to show it again. Window managers without `_NET_WM_STATE_HIDDEN` keep today's behaviour. | Fixed | A new Torquio Wine patch and a new engine image. | Low to moderate. Wine's window-state tracking is delicate: when Wine wants a window shown again, it unmaps and remaps an iconic window (a workaround for Mutter), which could pull the window onto the current workspace. The patch has to keep the window iconic until the window manager shows it. Suitable to offer upstream. |
| 2 | **Wine's Wayland driver** (`winewayland.drv`) instead of X11. | Fixed (tested) | Small to switch: the driver list in `HKCU\Software\Wine\Drivers`, or starting Wine without `DISPLAY`. | High for now. On GNOME, Wine draws Windows-style title bars (GNOME offers no server-side decorations, and Wine has no client-side ones yet). Torquio's X11-specific fixes (Dorico's popups and layered windows) don't apply. The clipboard is limited on GNOME. Dorico, its plug-in windows and the Activation Manager's sign-in are untested under it. This is the backlog's "Eventually switch to Wine Wayland driver" item. |
| 3 | **A Wine virtual desktop or gamescope:** all of a program's windows inside one desktop window. | Fixed (virtual desktop tested) | Small: a launcher option. | Not acceptable as a default. Dorico's windows (score, mixer, plug-in editors, dialogs) would live inside one Windows-style frame without GNOME's window management. The virtual desktop took the whole screen in the test. |

**Recommended: option 1.**

- It fixes the cause instead of working around it.
- It doesn't change how Torquio's windows look or behave.
- It needs no change to anyone's prefix, settings or Wine registry. It arrives with a new engine image, and
  Update Torquio offers it.

## Plan for option 1

1. **Write the patch** against the pinned Wine commit, as `scripts/1-build/patches/0014-...`. It must:
   - add the `_NET_WM_STATE_HIDDEN` atom;
   - track whether the current `_NET_WM_STATE` includes it;
   - only minimize the Windows window when an iconic window is hidden, or when the window manager doesn't
     support the flag;
   - while an un-hidden iconic window is still shown in Windows, keep the X11 window iconic instead of
     requesting `NormalState`.
2. **Build a test engine** in a throwaway container, never a user's.
3. **Test in GNOME on a test machine:**
   - the previews on another workspace;
   - minimizing and restoring from the title bar, the dock, the window switcher and the keyboard;
   - switching back to the workspace, and moving a window between workspaces;
   - dialogs and popups while the main window is on another workspace;
   - with Dorico: its windows, plug-in editors and playback while on another workspace.
4. **Check on KDE:** KWin's "Keep window thumbnails" setting has its own interplay with iconic windows.
5. **Ship it** in a release after v0.7.0, with the new engine image, and offer the patch upstream.

If option 1 turns out unsafe, Torquio keeps today's behaviour (black previews only) rather than switching drivers.
