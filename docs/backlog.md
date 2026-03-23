# Project Backlog & Granular Requirements

This document tracks the specific, nitty-gritty technical subtasks and implementation details required to fulfill the high-level To-Do items in the main blueprint.

## Epic: The Master Installer Wrapper
**Context:** We need a single-command `curl | bash` installation experience so Linux novices don't have to manually run individual scripts.

### Subtasks: Missing Component Scripts
We currently have `install_noteperformer.sh`, but we lack dedicated automation scripts for the core Steinberg components. Before we can build the master wrapper, we must build and test:
*   [ ] **`install_sda.sh`**:
    *   Must use a generalized glob pattern (e.g., `Steinberg_Download_Assistant_*_Installer_win.exe`) to find the user-provided installer regardless of the version number they downloaded.
    *   Must handle the execution inside the container prefix.
*   [ ] **`install_mediabay.sh`**:
    *   Currently, `setup_prefix.sh` unzips the MediaBay installer and deletes the broken `preinstall.ps1` file, but it doesn't *run* the actual setup.
    *   Need a dedicated script that navigates into the `MediaBay_extracted/` directory, dynamically finds the subfolder (e.g., `MediaBay 1.3.60` — this must be dynamic as versions will change), and executes `wine Setup.exe`.

### Subtasks: The "one-click" Bootstrapper (`install.sh`)
*   [ ] **Prerequisite Checks:** Script must check for `distrobox` (or `distroshelf`) and `docker`/`podman`. If missing, halt and print clear instructions to install them.
*   [ ] **Asset Validation:** Ensure an `installers/` directory exists and prompt the user to drop their `.exe` files into it before continuing.
*   [ ] **Execution Chain:** Sequentially call `build_wine.sh` -> `setup_prefix.sh` -> `install_sda.sh` -> `install_mediabay.sh` -> `install_noteperformer.sh`.

## Epic: UX/UI Desktop Integration
**Context:** Distrobox auto-exports `.desktop` files with icons, but we need our custom `.desktop` files to handle the `net-steinberg-sam://` URI schemes. 

### Subtasks: `.desktop` File Merging
*   [ ] The stubs in `desktop_stubs/` currently lack `Icon=` paths. 
*   [ ] Need a post-install script that runs `distrobox-export --app` for SDA, SAM, and Dorico.
*   [ ] Extract the generated `Icon=` lines from the Distrobox-exported files located in the host's `~/.local/share/applications/`.
*   [ ] Inject those Icon paths into our custom URI-handler stubs and overwrite the Distrobox ones, ensuring the user gets one clean icon that launches the app *and* handles the login links.