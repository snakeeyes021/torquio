# Plan: Torquio in Python (v0.6.0)

Status: **approved** (2026-10-24). Tracked as the v0.6.0 epic in `BACKLOG.md` ("Defined Work").

## 1. Goal

Rewrite Torquio's host-side Bash in dependency-free Python, so that it's legible and maintainable for its
maintainers (and contributors, and LLM-assisted work), with **no change in behaviour for users**: same
commands, flags, menus, wording, files and results. The new code is organised as a core library with a thin
command-line interface on top, which the v0.7.0 GUI (GTK4/libadwaita via PyGObject, for Flathub) will reuse
as a second interface.

Non-goals: new features, new dependencies, changing what runs inside the container, changing the user
interface. Bugs found along the way are fixed in separate, clearly labelled commits (so the port itself stays
a faithful translation).

## 2. Why Python (summary of the decision)

- Legibility: Python is the language the maintainers (and most contributors) read most comfortably.
- Fewer classes of bugs. The v0.5.0 work hit several Bash-specific ones: a helper's non-zero return under
  `set -e` silently aborting the dashboard, a background `distrobox enter` swallowing a prompt's input,
  `pkill -f` matching its own shell, nested quoting in the generated Dorico runner, word splitting on paths
  with spaces. Python runs commands with argument lists (no shell quoting) and makes errors explicit.
- Torquio already needs Python on the host (config reads/writes are Python one-liners inside Bash, as are the
  license checks, the manifest, the log export and graphics detection), so nothing new is required.
- Structured data (JSON config, Wine registry files, versions) and unit tests are natural in Python.
- The core can be shared with the v0.7.0 GUI.

## 3. Principles

1. **Identical behaviour.** Output text, colours, prompts, defaults, exit codes, files written and their
   locations stay the same. Deviations only as separate, listed bug fixes.
2. **Standard library only, Python 3.9+.** A `git clone` keeps working with nothing to install. Ubuntu 22.04
   and its family (Mint 21, Pop!_OS 22.04, Zorin 17, elementary 7) ship 3.10, the oldest of the maintained
   desktop distros; 3.9 also covers RHEL 9 and its rebuilds (AlmaLinux, Rocky), maintained until 2032. So no
   `match` statements, no `X | Y` unions evaluated at runtime (fine in annotations with
   `from __future__ import annotations`), no parenthesised multi-item `with`, `zip(strict=)`,
   `itertools.pairwise`, dataclass `slots=`/`kw_only=`, and none of 3.11+ (`tomllib`, `ExceptionGroup`,
   `typing.Self`). CI runs the unit tests on 3.9 to catch slips.
3. **Staged, never half-broken.** The Bash `torquio` stays the entry point while its functions are moved, one
   group per stage, into Python (the Bash function body becomes a call into Python). Every stage leaves
   Torquio fully working and is merged to develop on its own. The entry point and menu move last.
4. **Each stage is tested for parity** (section 7) before it's merged.
5. **Container-side code stays Bash** (section 5).

## 4. Target layout

```
torquio                          # entry point (Bash during the port; at the end a small Python script)
lib/torquio/                     # the package (not at the repo root: `torquio` is already a file there)
lib/torquio_bridge.py            # runs __main__ for Bash (a script, so the current directory can't shadow the package)
    __main__.py                  # internal commands Bash calls during the port (torquio_py in common.sh)
    paths.py                     # repo dir, XDG data/cache/config dirs, prefix, container name, overrides
    config.py                    # ~/.config/torquio/config.json (same keys and value types as today)
    ui.py                        # colours, clear, header, prompts (y/N, [Y/n], typed overrides), Ctrl+C
    session_log.py               # the per-session log mirror (today: exec > >(tee -i LOG) 2>&1)
    run.py                       # subprocess helpers: interactive passthrough, captured output, no-input
    container.py                 # manager detection, distrobox enter/create/rm, images, replace_container
    identity.py                  # machine ID: derived ID, container ID, fix_machine_identity
    engine.py                    # prebuilt image tag, pull, engine_outdated, update/rebuild Wine engine
    prefix.py                    # Wine commands in the prefix, registry edits, apply_prefix_settings, DPI
    gpu.py                       # NVIDIA detection, Vulkan GPUs, AI GPU setting, setup_gpu_access
    graphics.py                  # today's torquio_graphics.py + configure_graphics / diagnostics
    licenses.py                  # Steinberg + plug-in license detection (today: two scripts)
    projects.py                  # Dorico projects stored inside the prefix
    manifest.py                  # today's version_manifest.py
    logs.py                      # today's export_logs.py
    updates.py                   # self-update, post-update, update check, settings
    launchers.py                 # host-side icons/launchers/MIME handling (refresh_launchers)
    keycommands.py, folders.py, ntsync.py, settings.py
    install.py, uninstall.py     # today's install.sh and cleanup.sh
    launch/                      # today's torquio-dorico, torquio-sam, torquio-sda-handler
    versions.py                  # `sort -V` ordering
    cli/                         # the terminal interface: one module per screen (status = the dashboard,
                                 # graphics, header, usage, ...), later the menus and flag parsing
scripts/templates/run-dorico.sh.in   # the generated Dorico runner as a template file (no heredoc escaping)
tests/                           # unittest tests and the parity harness (section 7)
```

Rule of thumb: modules in `lib/torquio/` other than `ui.py`, `cli/` and `launch/` don't print or prompt;
they return values and raise exceptions, and the CLI (later also the GUI) decides what to show. Where a
function needs to ask the user something mid-way (e.g. the license guard), it takes a callback, so the CLI
asks in the terminal and the GUI in a dialog.

## 5. What stays Bash, and why

Code that runs **inside the container** (a minimal Ubuntu where Bash is the natural tool, and which the image
build also uses):

- `scripts/1-build/build_wine.sh`, `scripts/1-build/container_gpu_setup.sh`, the Containerfile
- `scripts/2-install/setup_prefix.sh` (winetricks, ICU, registry setup), `extract_icons.sh`'s
  `wrestool`/`icotool` part
- the generated Dorico runner (`run-dorico.sh`), moved into a template file

`scripts/cleanup_valerio.sh` (legacy migration from the old name) stays as it is.

Everything that runs **on the host** moves to Python: `torquio`, `scripts/common.sh`, `install.sh`,
`cleanup.sh`, the host-side `install_*.sh` helpers, the three launchers and the existing Python scripts.

## 6. Contracts that must never break

These are relied on by users, by older Torquio versions or by other parts of Torquio:

| Contract | Why |
|---|---|
| `./torquio`, `~/.local/bin/torquio` (symlink to the repo) and every flag and alias in `torquio`'s usage | users, README, desktop files, muscle memory |
| `torquio --post-update <old-commit> [--menu]` | v0.4.0 and v0.5.0's updaters run the *new* copy with exactly this after updating |
| Menu numbering and wording (main menu, Wine Tools, Settings, ...) | README references options by number |
| Exit codes: `10` = cancelled by the user (the installer checks it after running the uninstaller), `1` = error | installer ↔ uninstaller |
| `~/.config/torquio/config.json`: same keys, same value types (booleans stay JSON booleans) | existing installs |
| Launcher names in `~/.local/bin` (`torquio-dorico`, `torquio-sam`, `torquio-sda-handler`) | `.desktop` files and MIME handlers point at them |
| Log file names and locations (`~/.local/share/torquio/logs/torquio_<kind>_<timestamp>.log`) | log export, bug reports |
| `~/.local/share/torquio/run-dorico.sh`, prefix markers (`.torquio_core_installed`, `.torquio_cantai_template_added`), the engine's `build-info` | existing installs, the dcomp lab |
| Environment overrides: `TORQUIO_CONTAINER_NAME`, `TORQUIO_IMAGE_REPO`, `DBX_CONTAINER_MANAGER`, `XDG_*` | testing, advanced users |

The installed launchers become small stubs (same names) that run the package from the repo, found the way
`torquio-sda-handler` finds it today (an `@TORQUIO_REPO_DIR@` placeholder filled in when launchers are
installed). Updating Torquio refreshes them, as it does now.

## 7. Testing

**Parity harness** (`tests/parity/`): runs the current (Bash) and new (Python) code side by side in an isolated
environment (a scratch clone of the repo, scratch `XDG_*` directories, `TERM` set, a fake or test
container where needed), feeds both the same scripted input, and diffs their output byte for byte, colours
included. Timestamps are masked. Before porting a group, its flows are recorded from the Bash version; the
stage isn't done until the Python version matches. Used for everything that's safe to run repeatedly: menus,
help text, dashboard, settings, manifest, license and project detection, update notice, flag handling.

**Real tests on a real install** for what changes the system, with a checklist per stage, as for v0.5.0:
install from scratch, uninstall (guards), update from the previous release (the `--post-update` handover),
engine update and container swap (identity kept, Cantai stays activated), NVIDIA conversion, launching
Dorico / Activation Manager / Download Assistant (including web logins), folder mappings, key commands.

**Unit tests** (`python3 -m unittest discover tests`), standard library only, for the logic: engine-outdated
check, prebuilt tag, license and project detection, mimeapps and Wine-leftover cleanup, config handling,
registry and PE version parsing, manifest output, update-notice throttling.

**CI:** a small GitHub Actions workflow runs the unit tests on Python 3.9 and the newest 3.x (and ShellCheck on
the remaining Bash) on every push. It doesn't build the engine image and takes seconds.

## 8. Stages

Each stage is its own branch, tested (section 7) and merged to develop with the usual procedure. v0.6.0 is
released after the last stage; develop stays usable throughout.

| # | Stage | Moves to Python | Testing focus |
|---|---|---|---|
| 0 | Foundation | `lib/torquio/` skeleton, `paths`, `config` (replaces the Python one-liners in `common.sh`), `ui`, `run`; the manifest, log export and license checks move into the package (their old paths had only internal callers, so they're removed rather than wrapped; `torquio_graphics.py` stays until stage 6, because the launchers in `~/.local/bin` use a copy of it); Python version check; unit-test and parity harness, CI workflow | unit tests; parity of everything (nothing visible changes) |
| 1 | Read-only | dashboard (`show_status`), graphics diagnostics, header, help text, manifest | parity (dashboard on installed / not installed / no container) |
| 2 | Maintenance | Configure Graphics (and applying graphics settings), ntsync, key commands, folder mappings, run custom exe, prefix settings, Settings, update check, log export screen | parity of menus and of the commands sent to the container and desktop; real: mappings, key command export/import |
| 3 | Engine and container | `replace_container`, engine update/rebuild, `engine_outdated`, identity, GPU (setup, chooser, Vulkan list; they re-create the container), the Wine Tools menu (it calls all of these), self-update and `--post-update` | unit tests; real: update from v0.5.0 (handover), engine swap and back, NVIDIA conversion, Cantai stays activated |
| 4 | Uninstall | `cleanup.sh` (guards, project check, leftovers, display-scaling restore) | parity of guards with fixtures; real: uninstall, then sweep for leftovers |
| 5 | Install | `install.sh` and the host-side `install_*.sh`, launcher/icon installation | real: install from scratch (prebuilt and compile-from-source paths), repair, recreate container |
| 6 | Launchers | `torquio-dorico`, `torquio-sam`, `torquio-sda-handler`, graphics automation; runner template | real: launch Dorico on GNOME (and KDE if available), scaling, web logins (SAM, SDA), opening .dorico files |
| 7 | Entry point | the menu loop and flag parsing; `torquio` becomes a small Python entry point; dead Bash removed; docs (ARCHITECTURE, AGENTS, CONTRIBUTING) | parity of every menu and flag; real: full regression pass; then release v0.6.0 |

## 9. Risks and how they're handled

| Risk | Handling |
|---|---|
| Interactive programs (winetricks output, `sudo` prompts, distrobox's first-start setup, podman's download progress) don't reach the terminal as before | `run.py` has one helper for interactive commands (inherits the terminal) and one for captured output, chosen deliberately per call; parity and real tests cover each install/update flow |
| The session log mirror behaves differently | `session_log.py` reproduces today's redirection exactly: stdout and stderr go through a `tee -i` child into the log, so child programs see the same pipe they see today |
| Ctrl+C prints a Python traceback | one handler in `cli/`: prints what the Bash version prints (or nothing) and exits with the same code |
| Prompt behaviour at end of input (scripts, pipes) differs | `ui.ask` mirrors `read -p`: at end of input it stops Torquio with exit code 1 where `set -e` did (no `|| true`, not called from an `if`), and returns the partial answer elsewhere; covered by scenarios that end input early |
| Python reads ahead and swallows input meant for the Bash code after it (found in stage 2: piped input lost the main menu's next answer) | `ui.read` reads stdin a byte at a time, as Bash's `read` does; scenarios with piped input |
| Background container commands swallow keyboard input meant for a prompt | `run.py` gives non-interactive commands no input (`stdin=DEVNULL`) by default |
| The update handover breaks for people updating from v0.4.0/v0.5.0 | stage 3 tests a real update from v0.5.0; `--post-update` keeps working forever |
| Installed launchers can't find the package | stubs with the repo path filled in at install time (as `torquio-sda-handler` does today); tested in stage 6 with a fresh install and an update |
| Mixed Bash/Python period adds moving parts | Bash only calls into Python through `torquio_py <command>` in `common.sh` (one place); each stage merged only when fully tested |
| Host Python older than 3.9 | checked at startup (in the Bash entry point while it exists, then in the Python one, written so it still parses on old Pythons) with a clear message, e.g. "Torquio needs Python 3.9 or newer (yours is 3.6); install a newer python3 package." Affects openSUSE Leap 15 and RHEL 8 (default `python3` is 3.6); today nothing checks |

## 10. Deliberate differences so far

Fixed or changed on purpose, each in its own commit (everything else is meant to be identical):

- Log export: the settings are read from `~/.config/torquio/config.json`, where Torquio writes them (it looked
  under `$XDG_CONFIG_HOME`).
- Configure Graphics: the Wayland-only error and the "back up your current desktop scaling settings" lines
  have their intended colours; a folder already mapped to a drive letter no longer shows a stray `033[0m`.
- Edge cases where Bash printed its own error (`[: : integer expression expected`, e.g. graphics data without
  `target_xwayland_factor`) now just take the same branch silently.
- Key command export after mapping a Desktop folder in the same session: Bash had sourced `user-dirs.dirs`
  by then, so a localised Downloads folder could be used; it now always uses `$XDG_DOWNLOAD_DIR` or
  `~/Downloads`, as the code intends.

## 11. Conventions

- PEP 8, readable names, docstrings and comments in the style of the existing Python scripts (say why, not
  what); type hints where they help.
- Commands run through `run.py` with argument lists, never shell strings (except where a command has to run
  a shell inside the container, e.g. `distrobox enter ... -- bash -c`, which stays explicit and quoted with
  `shlex.quote`).
- User-facing wording stays next to the code that shows it (as today), not in a separate strings file.
- One module per area; no module over ~600 lines.
