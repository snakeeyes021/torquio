# Project Backlog

This document is the single source of truth for all tasks, bugs, and enhancements.

## Defined Work (Sprint)
This section tracks epics that have been broken down into concrete, actionable subtasks.

### Epic: The Master Installer Wrapper (User Experience)
**Context:** Assuming Steinberg legal does not allow pre-packaged distribution, the end-user will need to provide their own `.exe` and `.zip` installers. We must not force Linux novices to use `git clone` or run multiple shell scripts. We need a single-command `curl | bash` installation experience. *(Note: The exact sequence this master script must automate is codified in `docs/PLAYBOOK.md`.)*

#### Subtasks: Missing Component Scripts
We currently have `install_noteperformer.sh`, but we lack dedicated automation scripts for the core Steinberg components. Before we can build the master wrapper, we must build and test:
*   [x] **`install_sda.sh`**:
    *   Must use a generalized glob pattern (e.g., `Steinberg_Download_Assistant_*_Installer_win.exe`) to find the user-provided installer regardless of the version number they downloaded.
    *   Must handle the execution inside the container prefix.
*   [x] **`install_mediabay.sh`**:
    *   Move the unzip logic currently inside `setup_prefix.sh` into this dedicated script. It should look for the user-provided `.zip` inside the designated `installers/` directory rather than the repo root.
    *   After unzipping, the script must perform a **recursive cleanup** of blocked files (e.g., `preinstall.ps1`) within the extracted directory to prevent "Not Trusted" error code 231.
    *   After cleanup, navigate into the versioned subfolder and execute `wine Setup.exe`.
*   [ ] **`update_mediabay.sh` (or CLI Updater Mode):**
    *   SDA attempts to update MediaBay but fails due to the `preinstall.ps1` block (Error 231). We need to refactor `install_mediabay.sh` and/or the SDA's launcher (.desktop file or shell script) to handle subsequent updates (e.g., pre-emptively manually checking for updates prior to and outside of the SDA running; if an update is found, we automatically download the installer (which may be a feature we add in the future anyways), clean it, and finally run the new installer ALL BEFORE running the SDA).

#### Subtasks: The "one-click" Bootstrapper (`install.sh`)
*   [x] **The Curl Command:** Create a single terminal command (e.g., `curl -sL ... | bash`) that users copy/paste from the GitHub README to download the installer framework.
*   [x] **Prerequisite Checks:** Script must check for `distrobox` (or `distroshelf`) and `docker`/`podman` (prompting the user to install them via Flatpak/system packages if missing). If missing, halt and print clear instructions to install them.
*   [x] **Asset Validation:** Ensure an `installers/` directory exists and prompt the user to drop their `.exe` files into it before continuing.
*   [x] **Execution Chain:** Sequentially call `build_wine.sh` -> `setup_prefix.sh` -> `install_sda.sh` -> `install_mediabay.sh` -> `install_noteperformer.sh`.
*   [x] **Final Integration:** Automatically register the `.desktop` stubs and MIME types.
*   [x] **Cleanup/Uninstaller Script (`scripts/cleanup.sh`):** Create a robust script to wipe the environment (container, XDG share/cache dirs, and host integrations) to allow for clean re-installs or uninstallation.

### Epic: UX/UI Desktop Integration
**Context:** Distrobox auto-exports `.desktop` files with proper icons, conflicting with our custom manual ones which handle the `net-steinberg-sam://` URI schemes. We need to merge the "Nice Icon" with the "Functional Link Handler" and establish actual scripted functionality. There may be other good stuff in the exported .desktop files that we want in ours.

#### Subtasks: .desktop File Merging
*   [x] **Suppress winemenubuilder:** Wine automatically creates `.desktop` links for Windows applications and file extensions (e.g., in `~/.local/share/applications/wine/Programs/`). This pollutes the host environment. We need to export `WINEDLLOVERRIDES="winemenubuilder.exe=d"` in our installation scripts so Wine stops spamming the host's app menu. *Note: When we write the cleanup script for these, it must be carefully targeted (e.g., only deleting Steinberg/Dorico specific files) so we don't accidentally wipe a user's desktop files from other non-Valerio Wine prefixes.*
*   [x] Use the current "messy" state of the host machine as a diagnostic baseline.
*   [x] The stubs in `desktop_stubs/` currently lack `Icon=` paths. 
*   [x] Need a post-install script that runs `distrobox-export --app` for SDA, SAM, and Dorico. (Implemented a cleaner, Distrobox-independent solution via surgical `wrestool` extraction).
*   [x] Extract the generated `Icon=` lines from the Distrobox-exported files located in the host's `~/.local/share/applications/`. (Bypassed via surgical extraction).
*   [x] Inject those Icon paths into our custom URI-handler stubs and overwrite the Distrobox ones, ensuring the user gets one clean icon that launches the app *and* handles the login links.
*   [x] **MIME/Protocol Handler Priority:** Resolve the conflict where GNOME prompts the user to choose between the "SDA" and the "SDA Handler" when clicking login links. Ensure our handler is the default for `net-steinberg-*` protocols (OR, preferably, the SDA itself and the SDA handler need to be the same thing somehow so the choice couldn't even exist in the first place--our handlers are essentially hacks that we overlay on top of a legitimate Dorico install; we want to get as close to normal native function as possible). (Resolved by unifying into a single stub per application).
*   [x] Investigate: currently, with both our custom .desktop files and the Distrobox-exported ones, GNOME/Wayland are using the icons from the Distrobox-exported file for displaying running apps in the dash and overview (and in the app picker lists for running unknown file types). We need to see if that still occurs when there is only our correct one, and if so, we need to figure out how to fully integrate ours into these system functions. (Resolved via `StartupWMClass` metadata).

### Epic: Engine Dependency Automation (libicu)
**Context:** Wine requires native ICU support for core Unicode translation, and Steinberg apps require Windows-side ICU binaries within the prefix.
*   [x] **Native Dependencies:** Added `winetricks`, `unzip`, and `cabextract` to `scripts/1-build/build_wine.sh`.
*   [x] **Prefix Dependencies:** Automated `wine-icu-72.1` download and silent MSI installation in `scripts/2-install/setup_prefix.sh`.
*   [ ] **Cleanup:** Delete `scripts/1-build/TO_BE_DELETED_rebuild_wine_icu.sh` once the above are verified working in a fresh build.

### Epic: Documentation & Repository Polish
**Context:** Prepare the repository for public consumption and preserve AI agent context.
*   [ ] **Update Main README:** Refactor `README.md` to be strictly user-facing (What is it, prerequisites, installation). Move developer/architectural deep-dives to `docs/ARCHITECTURE.md`.
*   [ ] **Add Standard Open Source Docs:** Create `CONTRIBUTING.md` and `LICENSE` files.

## Undefined Work (Backlog)
This section tracks high-level goals and ideas that have not yet been broken down into concrete subtasks.

*   [ ] **Container Digest Pinning:** To achieve maximum reproducibility and avoid potential issues with rolling `apt` updates on the host image, investigate pinning the Distrobox container to a specific SHA256 digest (e.g., `ubuntu@sha256:...`) rather than the floating `ubuntu:24.04` tag in the automated installer. We may actually NOT want to do this, as using an LTS may already be sufficient for reproducibility and any updates that get pushed to that OS version will likely be security patches and so forth but that do not affect API or binary compatibility.
*   [x] **Production Path Refactoring:** Transition from isolated development paths (`~/dev/...`) to standard production paths.
    *   Removed hardcoded `$HOME/dev/steinberg-on-linux` references in `build_wine.sh` and `setup_prefix.sh` and replaced them with dynamic workspace variables and XDG-compliant paths.
    *   Scripts now dynamically generate the Wine prefix in a user-agnostic XDG location (`~/.local/share/valerio/prefix`).
    *   Added `scripts/common.sh` for shared environment variables.
*   [ ] **Suppression of `rundll32` Errors:** During prefix initialization and `winetricks` execution, some `rundll32` errors may occur. Investigate their cause and implement suppression (e.g., via `WINEDEBUG=-all` for specific phases) to avoid confusing users.
*   [ ] **File assocations:** Clicking on Dorico files in the file explorer brings up a "Could Not Display "FILENAME.dorico" There is no app installed for "Dorico Project" files. 
*   [ ] **Keyboard Auto-Repeat Bug:** Holding a key combination results in rapid-fire, delayed inputs that continue executing after the keys are released. This is a known XWayland/Wine event-loop quirk. Investigate solutions (e.g., tweaking X11 auto-repeat rates via `xset r rate` before launch, or exploring Wine registry input tweaks).
*   [ ] **High-DPI / 4K Scaling:** Wine isn't scaling automatically on one particular 4K 28" screen (not sure about other 4K screens). We need to investigate Wine DPI registry keys or a dynamic DPI switcher alias. ALSO, new discovery: turning off xwayland scaling sizes the app correctly, but things are blurry, so what probably needs to happen is that anytime you start the app, the launcher checks if that's off, if off, turns it on, then it checks the dpi of the monitor and sets the wine dpi settings accordingly. Closing it should set everything back. -- Extra info/context: xwayland-native-scaling being turned off seems to fix this but also seems to cause blurriness. Ideally, we could have one solution that, at application launch, checks the monitor, its actual size and/or actual/recommended DPI, and whatever else, and automatically sets some settings just for Dorico. This means if a user ferries their 1080p laptop back and forth between a 4k dock, every launch will launch at the right resolution. Additionally, if it's possible to monitor what screen Dorico is on at any given moment and adjust the DPI accordingly on the fly, that would be even better, assuming it's possible.  
*   [ ] **VSTAudioEngine6.exe Crash:** The audio engine crashes cleanly upon closing Dorico. This does not prevent proper function of the application; it's just ugly/annoying. Need to investigate if this is a Pipewire/ASIO routing issue or a Wine teardown bug.
*   [ ] **Visual Glitches / GE-Proton Experiment:** The current `zhiyi/wine` build has transparent text in SDA and font ugliness. Create an experimental Git branch to try patching `dcomp` directly onto an *optimal* version of GE-Proton (known working verison of GE Proton without the visual glitches: GE Proton 10.33, but we probably want to test against either GE Proton current, GE Proton rc, or whatever GE Proton matches zhiyi/wine).
*   [ ] **GNOME / Adwaita Theming:** Investigate applying a Windows `.msstyles` theme to make Wine scrollbars and menus match GNOME/Adwaita natively. Explore having this run automatically if GNOME is detected. Consider doing the same for KDE, or just leaving it for KDE and all other DEs.
*   [ ] **Version Manifest Generation:** Programmatically extract and record the exact version numbers of every piece of installed Steinberg software to create a reproducible manifest.
*   [ ] **User Configuration Sync:** Create scripts to automate the backup/export and restoration of user key commands (`keycommands*.json`) and other critical preference files.
*   [ ] **Automated 1st-Party Downloads:** Investigate and implement automated download fallbacks for 1st-party Steinberg components (SDA, MediaBay) if they are missing from the `installers/` directory.
*   [ ] **System-Wide Logging:** Implement a structured logging framework (e.g., redirecting stdout/stderr to `~/.local/state/valerio/logs/`) to provide users with a "debug bundle" they can share when hitting issues.
*   [ ] **"License Eater" Bug:** On prior attempts in Bottles, a (assumed) hardware fingerprinting issue is causing licenses to disappear. Determine if the issue exists under our current method, and, if so, figure out a strategy for maintaining hardware fingerprint (if that is the problem).
*   [ ] **NotePerformer UI:** Fix graphical glitches in the NotePerformer VST window. (Determine if this is still an issue under the current custom Wine build).
*   [ ] **"Edit Instrument"** Attempting to edit a VST instrument from within Play mode causes a crash/hang/failure. Investigate.
*   [ ] **Opening Files** Clicking on Dorico files from the file explorer does nothing. Dorico (with the proper icon) is set as the program to open the files, but that isn't the Dorico we use to launch Dorico, so that's likely the issue. Investigate.
*   [ ] **NotePerformer Splash Screen Icon (Low Priority):** When NotePerformer briefly launches its splash screen, it lacks an icon in the Wayland overview/dash. This can likely be solved via the same icon/StartupWMClass extraction we used for the main apps. We need to get the hardcoded path of the NotePerformer exe, extract the icon, and assign it to a hidden .desktop file.

## Done
*(Move completed epics and tasks here for historical record)*
