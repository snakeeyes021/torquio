# Project Backlog

This document is the single source of truth for all tasks, bugs, and enhancements.

## Defined Work (Sprint)
This section tracks epics that have been broken down into concrete, actionable subtasks.

### Epic: The Master Installer Wrapper (User Experience)
**Context:** Assuming Steinberg legal does not allow pre-packaged distribution, the end-user will need to provide their own `.exe` and `.zip` installers. We must not force Linux novices to use `git clone` or run multiple shell scripts. We need a single-command `curl | bash` installation experience. *(Note: The exact sequence this master script must automate is codified in `docs/PLAYBOOK.md`.)*

#### Subtasks: Missing Component Scripts
We currently have `install_noteperformer.sh`, but we lack dedicated automation scripts for the core Steinberg components. Before we can build the master wrapper, we must build and test:
*   [ ] **`install_sda.sh`**:
    *   Must use a generalized glob pattern (e.g., `Steinberg_Download_Assistant_*_Installer_win.exe`) to find the user-provided installer regardless of the version number they downloaded.
    *   Must handle the execution inside the container prefix.
*   [ ] **`install_mediabay.sh`**:
    *   Move the unzip logic currently inside `setup_prefix.sh` into this dedicated script. It should look for the user-provided `.zip` inside the designated `installers/` directory rather than the repo root.
    *   After unzipping and deleting the broken `preinstall.ps1`, the script must navigate into the `MediaBay_extracted/` directory, dynamically find the subfolder (e.g., `MediaBay 1.3.60` — this must be dynamic as versions will change), and execute `wine Setup.exe`.

#### Subtasks: The "one-click" Bootstrapper (`install.sh`)
*   [ ] **The Curl Command:** Create a single terminal command (e.g., `curl -sL ... | bash`) that users copy/paste from the GitHub README to download the installer framework.
*   [ ] **Prerequisite Checks:** Script must check for `distrobox` (or `distroshelf`) and `docker`/`podman` (prompting the user to install them via Flatpak/system packages if missing). If missing, halt and print clear instructions to install them.
*   [ ] **Asset Validation:** Ensure an `installers/` directory exists and prompt the user to drop their `.exe` files into it before continuing.
*   [ ] **Execution Chain:** Sequentially call `build_wine.sh` -> `setup_prefix.sh` -> `install_sda.sh` -> `install_mediabay.sh` -> `install_noteperformer.sh`.
*   [ ] **Final Integration:** Automatically register the `.desktop` stubs and MIME types.

### Epic: UX/UI Desktop Integration
**Context:** Distrobox auto-exports `.desktop` files with proper icons, conflicting with our custom manual ones which handle the `net-steinberg-sam://` URI schemes. We need to merge the "Nice Icon" with the "Functional Link Handler" and establish actual scripted functionality. There may be other good stuff in the exported .desktop files that we want in ours.

#### Subtasks: .desktop File Merging
*   [ ] Use the current "messy" state of the host machine as a diagnostic baseline.
*   [ ] The stubs in `desktop_stubs/` currently lack `Icon=` paths. 
*   [ ] Need a post-install script that runs `distrobox-export --app` for SDA, SAM, and Dorico.
*   [ ] Extract the generated `Icon=` lines from the Distrobox-exported files located in the host's `~/.local/share/applications/`.
*   [ ] Inject those Icon paths into our custom URI-handler stubs and overwrite the Distrobox ones, ensuring the user gets one clean icon that launches the app *and* handles the login links.
*   [ ] Investigate: currently, with both our custom .desktop files and the Distrobox-exported ones, GNOME/Wayland are using the icons from the Distrobox-exported file for displaying running apps in the dash and overview (and in the app picker lists for running unknown file types). We need to see if that still occurs when there is only our correct one, and if so, we need to figure out how to fully integrate ours into these system functions.

### Epic: Engine Dependency Automation (libicu)
**Context:** Wine requires native ICU support for core Unicode translation, and Steinberg apps require Windows-side ICU binaries within the prefix.
*   [ ] **Native Dependencies:** Add `libicu-dev` and `libicu-dev:i386` to the `apt-get install` list in `scripts/1-build/build_wine.sh`.
*   [ ] **Prefix Dependencies:** Add `curl` or `wget` commands to download `wine-icu-72.1-x86.msi` and `wine-icu-72.1-x86_64.msi` from WineHQ, and run silent installation (`wine msiexec /i`) in `scripts/2-install/setup_prefix.sh`. (Note: the versions of the wine-icu msi's that we download and install should be whichever version has been tested against that container image release)
*   [ ] **Cleanup:** Delete `scripts/1-build/TO_BE_DELETED_rebuild_wine_icu.sh` once the above are verified working in a fresh build.

### Epic: Documentation & Repository Polish
**Context:** Prepare the repository for public consumption and preserve AI agent context.
*   [ ] **Update Main README:** Refactor `README.md` to be strictly user-facing (What is it, prerequisites, installation). Move developer/architectural deep-dives to `docs/ARCHITECTURE.md`.
*   [ ] **Add Standard Open Source Docs:** Create `CONTRIBUTING.md` and `LICENSE` files.

## Undefined Work (Backlog)
This section tracks high-level goals and ideas that have not yet been broken down into concrete subtasks.

*   [ ] **Production Path Refactoring:** Transition from isolated development paths (`~/dev/...`) to standard production paths.
    *   Remove hardcoded `$HOME/dev/steinberg-on-linux` references in `build_wine.sh` and `setup_prefix.sh` and replace them with dynamic workspace variables (e.g., `WORKSPACE_DIR="$(pwd)"` or `WORKSPACE_DIR="$HOME/.local/share/steinberg-on-linux"`).
    *   Scripts must be updated to dynamically generate the Wine prefix in a user-agnostic XDG location (e.g., `~/.local/share/wineprefixes/dorico`) rather than the repo directory.
*   [ ] **High-DPI / 4K Scaling:** Wine isn't scaling automatically on one particular 4K 28" screen (not sure about other 4K screens). We need to investigate Wine DPI registry keys or a dynamic DPI switcher alias. ALSO, new discovery: turning off xwayland scaling sizes the app correctly, but things are blurry, so what probably needs to happen is that anytime you start the app, the launcher checks if that's off, if off, turns it on, then it checks the dpi of the monitor and sets the wine dpi settings accordingly. Closing it should set everything back.
*   [ ] **VSTAudioEngine6.exe Crash:** The audio engine crashes cleanly upon closing Dorico. This does not prevent proper function of the application; it's just ugly/annoying. Need to investigate if this is a Pipewire/ASIO routing issue or a Wine teardown bug.
*   [ ] **Visual Glitches / GE-Proton Experiment:** The current `zhiyi/wine` build has transparent text in SDA and font ugliness. Create an experimental Git branch to try patching `dcomp` directly onto an *optimal* version of GE-Proton (known working verison of GE Proton without the visual glitches: GE Proton 10.33, but we probably want to test against either GE Proton current, GE Proton rc, or whatever GE Proton matches zhiyi/wine).
*   [ ] **GNOME / Adwaita Theming:** Investigate applying a Windows `.msstyles` theme to make Wine scrollbars and menus match GNOME/Adwaita natively. Explore having this run automatically if GNOME is detected. Consider doing the same for KDE, or just leaving it for KDE and all other DEs.
*   [ ] **Version Manifest Generation:** Programmatically extract and record the exact version numbers of every piece of installed Steinberg software to create a reproducible manifest.
*   [ ] **"License Eater" Bug:** On prior attempts in Bottles, a (assumed) hardware fingerprinting issue is causing licenses to disappear. Determine if the issue exists under our current method, and, if so, figure out a strategy for maintaining hardware fingerprint (if that is the problem).
*   [ ] **NotePerformer UI:** Fix graphical glitches in the NotePerformer VST window. (Determine if this is still an issue under the current custom Wine build).
*   [ ] **"Edit Instrument"** Attempting to edit a VST instrument from within Play mode causes a crash/hang/failure. Investigate.
*   [ ] **Opening Files** Clicking on Dorico files from the file explorer does nothing. Dorico (with the proper icon) is set as the program to open the files, but that isn't the Dorico we use to launch Dorico, so that's likely the issue. Investigate.

## Done
*(Move completed epics and tasks here for historical record)*
