# Architectural Design & Blueprint

This document details the technical implementation and design philosophy of the Torquio framework (formerly Valerio) for running Steinberg software on Linux. It is intended for developers, maintainers, and AI agents modifying the system.

## 1. Core Architecture: The Container Method

We use a containerized approach using Distrobox and Docker (or Podman) to isolate the complex dependencies of Steinberg software from the host Linux system.

*   **The Engine:** We compile a custom branch of Wine (`zhiyi/wine`) from source (`https://gitlab.winehq.org/zhiyi/wine`), checked out at the commit pinned in `scripts/1-build/build_wine.sh`, which includes experimental `dcomp` stubs required by Dorico 6, plus Torquio's patches (`scripts/1-build/patches/`).
*   **The Prebuilt Image:** GitHub Actions (`.github/workflows/container-image.yml`) builds the container image (`scripts/1-build/Containerfile`: Ubuntu 24.04 + the compiled engine in `/opt/wine-custom` + its runtime libraries, 64- and 32-bit) and publishes it publicly as `ghcr.io/snakeeyes021/torquio-env`. Images are tagged `build-<hash>` with the git tree hash of `scripts/1-build`, which the installer computes from its own checkout (`torquio_prebuilt_image` in `scripts/common.sh`), so every copy of Torquio gets the engine built from exactly its build files. Without a matching image (not published yet, local changes to `scripts/1-build`, or `"build_from_source": true` in the config) the installer starts from plain `ubuntu:24.04` and compiles Wine locally as before. Updating the engine means pulling the new image and re-creating the container (`replace_container` in `torquio`); the Wine prefix lives in the user's home and is untouched. The image contains only free and open-source software, and ships the complete patched Wine source it was compiled from (`/opt/wine-custom/share/torquio/source/`, for the LGPL).
*   **The Environment:** Distrobox allows us to run an Ubuntu container that shares the host's display, DBus, audio, and home directory. Developing inside this container prevents pollution of the host system and avoids complex flatpak/appimage packaging during the core development phase.
*   **The Handoff:** Custom `.desktop` URI handlers on the host catch `net-steinberg-sam://`, `net-steinberg-sda://`, and `net-steinberg-activation-manager://` login tokens from the native Linux web browser and pass them directly into the containerized Windows binaries via Wine.
*   **Native DBus Browser Redirection:** This exists as a workaround to our disabling of the wineconsole (which we do to suppress annoying crash messages that don't actually affect the running of the app; we route these to log files though so they're not lost, as discussed below). Subsequently, to allow the containerized Windows applications to launch login links back in the host's native browser, we override the standard `winebrowser.exe` in the prefix. By mapping the `http` and `https` registry classes (`HKCR\http\shell\open\command`) to run a host-facing `busctl` command targeting `org.freedesktop.portal.Desktop OpenURI`, we achieve a complete browser redirection loop back to the host.

### Current Base Environment Details
*   **Container Host:** Distrobox (Ubuntu 24.04).
*   **Engine:** Docker or Podman (checked during installation).
*   **Custom Wine Build Source:** `https://gitlab.winehq.org/zhiyi/wine` at commit `ae88a705b5aa544cc60153d48c1ca8849f32ee14`.
    *   *Why:* Includes DirectComposition (`dcomp`) stubs required by Dorico 6.
    *   *Build Specifics:* Compiled with native multilib development libraries inside the container environment.
*   **Prefix Config:** Windows 10 (via Winetricks).
*   **Core Dependencies:** `d3dx9`, `msls31`, `allfonts`, `d3dcompiler_43`, `d3dcompiler_47`, `vcrun2019`, `dotnet48`, `wine-icu` (downloaded and installed as manual MSI packages).
*   **Custom Debugger Helper (`torquio-winedbg.exe`):** A custom Windows GUI debugger wrapper compiled from `scripts/1-build/torquio-winedbg.c` with the Wine engine (`build_wine.sh`, so it ships in `/opt/wine-custom/bin` of the prebuilt image too). Registered as the system AeDebug handler, it intercepts crash notifications and writes them to logs in `~/.local/share/torquio/logs/`. It silences harmless exit crashes (such as `VSTAudioEngine6.exe` on close) and prevents annoying Wine console debug windows from popping up.
*   **Registry Optimizations & Fixes:**
    *   *Modal Window Focus Loss:* Configures the X11 Driver with `FocusOnClick="Y"` and `UseTakeFocus="N"` to prevent keyboard focus lockups when closing modal sub-dialogs under GNOME.
    *   *Keyboard Auto-Repeat Lag:* Configures keyboard response accessibility settings (`AutoRepeatDelay="250"`, `AutoRepeatRate="30"`, `Flags="126"`) to resolve rapid-fire key repeat issues.
    *   *Font Anti-Aliasing:* Injects ClearType font smoothing registry keys (`FontSmoothing="2"`, orientations, and subpixel gamma settings) along with X11 Driver ClientSide rendering overrides for sharp UI text.

## 2. Delivery Mechanisms & The CLI App

The project has evolved from raw bootstrap scripts into a unified CLI orchestrator and manager:

**The `torquio` Console Manager (Current State):** A unified CLI runner (`./torquio` in the repository, symlinked to `~/.local/bin/torquio` on the host) that manages the lifecycle of the environment. Running it without flags spawns an interactive text-based setup and configuration wizard. It also supports CLI flags (`-i`/`--install`, `-r`/`--uninstall`, `-g`/`--graphics`, `-s`/`--status`, etc.) for silent script-based execution.  

**Future potential delivery improvements:**
1.  **AppImage / Flatpak:** If legally permitted (not likely), packing the engine and binaries into a single, executable AppImage or Flatpak manifest. Nonetheless, we may still want to move distribution of Torquio to Flatpak for its ease of installation/user-friendliness.

## 3. Execution Pipeline & Infrastructure

The project's scripting is organized chronologically to represent the build-to-runtime lifecycle:

*   **`torquio`**: The top-level orchestrator in the root directory. It processes flags, manages the CLI configuration profile (`~/.config/torquio/config.json`), coordinates Wine prefix boots/kills, and maps custom host project folders directly into the prefix drive letters.
*   **`scripts/install.sh`**: The top-level setup orchestrator. It verifies system requirements (Distrobox/Docker/Podman), builds the container, and runs the compilation and installer scripts in sequence.
*   **`scripts/cleanup.sh`**: The environment uninstaller/wipe script (its session log setup; the uninstaller itself is `lib/torquio/cli/uninstall.py` and `lib/torquio/uninstall.py`). It purges host stubs, container environments, directories, icons, and desktop associations, with scaling factor restore hooks, after the license and project guards.
*   **`scripts/cleanup_valerio.sh`**: A migration cleanup helper to purge the legacy "Valerio" environment details and configurations (for users who installed before the name change).
*   **`scripts/1-build/`:** Contains `build_wine.sh` which installs compile-time dependencies, clones the custom Wine git source, compiles both 64-bit and 32-bit (WoW64) versions, installs the binaries to `/opt/wine-custom` within the container and records what they were built from (`/opt/wine-custom/share/torquio/build-info`). The same script builds the engine in the prebuilt image (`Containerfile`).
*   **`scripts/2-install/`:** Contains scripts that bootstrap the Wine prefix (`setup_prefix.sh`), compile the custom debugger helper, and silently install MediaBay (`install_mediabay.sh`), the Download Assistant (`install_sda.sh`), and optional NotePerformer (`install_noteperformer.sh`).
*   **`scripts/3-runtime_handlers/`:** Runtime wrappers (`torquio-dorico`, `torquio-sam`, `torquio-sda-handler`) that are copied to the host's `~/.local/bin/`. They handle environmental setup, dynamic scaling application, and pass commands inside the container. `torquio_graphics.py` queries host monitor geometries to determine target DPI and desktop scaling.
*   **`lib/torquio/`:** Torquio's host-side Python package (standard library only, Python 3.9+), which the Bash is being ported into for v0.6.0 (`docs/REFACTOR.md`). During the port, Bash calls it only through `torquio_py` in `scripts/common.sh` (e.g. `torquio_py config-get KEY DEFAULT`, which `get_config_val` uses). It holds the paths, the settings file, the version manifest, the log exporter, the license checks, read-only container/engine/identity/graphics queries, folder mappings, prefix commands, and (in `cli/`) the header, the Status Dashboard, Configure Graphics, folder mappings, key commands, Settings, Wine Tools, the engine/container/GPU/identity tools, Update Torquio and its post-update step so far.
*   **`tests/`:** Unit tests (`python3 -m unittest`, run by `.github/workflows/tests.yml` on Python 3.9 and the newest 3.x, plus ShellCheck) and the parity harness (`tests/parity/`), which runs Torquio flows before and after a change in an isolated scratch environment and compares what the user sees.
*   **`desktop_stubs/`:** Templates for the host OS integration, linking the user's application menu and web browser back to the runtime handlers.

## 4. Desktop Integration & File Association Quirks

Because we actively suppress Wine's native host integrations (via `WINEDLLOVERRIDES="winemenubuilder.exe=d"`), we must manage desktop integrations manually:

*   **SDA Interaction & Polling:** The Steinberg Download Assistant (SDA) launches background daemons. The master installer polls the container's process list to ensure the SDA has exited before concluding.
*   **Surgical Icon Extraction:** Instead of relying on Wine or Distrobox exports, we programmatically extract high-resolution icons directly from the Windows executables (`Dorico.exe`, etc.) inside the container using `wrestool`. To comply with freedesktop.org specifications, application icons are installed to `apps/` and document icons to `mimetypes/` under the host's `~/.local/share/icons/hicolor/`.
*   **Quote Injection & Translation:** Host wrapper scripts accept standard Linux paths, but they must securely translate these via `winepath -w` *inside* the container, suppressing Wine's debug outputs (`WINEDEBUG=-all`), and passing the result as a strict positional argument to prevent bash interpolation errors.
*   **MIME Registration & Cache Override:** To securely associate project files (like `.dorico`, `.vstsound`, `.slm`), we inject MIME XML definitions into `~/.local/share/mime/packages/`. We then explicitly default our custom `.desktop` stubs as handlers (via `xdg-mime default`) to prevent leftover Wine-generated `.desktop` files from intercepting clicks.
*   **Window Manager Class (`StartupWMClass`):** GNOME uses the `StartupWMClass` to map running XWayland/Wine windows back to their launchers in the App Grid. Wine typically broadcasts the exact TitleCase string of the executable (e.g., `Dorico6.exe` or `Dorico.exe`). The `.desktop` stub must match this exactly to ensure running icons map correctly.