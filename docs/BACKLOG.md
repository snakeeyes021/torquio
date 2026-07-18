# Project Backlog

This document is the single source of truth for all tasks, bugs, and enhancements.

## Defined Work (Sprint)
This section tracks epics that have been broken down into concrete, actionable subtasks.


## Undefined Work (Backlog)
This section tracks high-level goals and ideas that have not yet been broken down into concrete subtasks.

*   [ ] **Suppression of `rundll32` Errors:** During prefix initialization and `winetricks` execution, some `rundll32` errors may occur. Investigate their cause and implement suppression (e.g., via `WINEDEBUG=-all` for specific phases) to avoid confusing users.
    *   *Update (Active Research)*: Evaluated native Wayland drivers and determined that `winewayland.drv` introduces major window management regressions (missing titlebars, buggy snapping under GNOME). Confirmed the optimal scaling bypass is setting GNOME's `xwayland-scaling-factor` to `1` (which disables compositor overscaling and renders 1:1, a setting KDE Plasma already defaults to via "Apply scaling themselves"), and then scaling Dorico internally using Wine's DPI (e.g. 120 DPI). Investigating integrating a dynamic GSettings trap/wrapper in the launchers and an automated display DPI detection profile.
*   [ ] **Version Manifest Generation:** Programmatically extract and record the exact version numbers of every piece of installed Steinberg software to create a reproducible manifest.
*   [ ] **Automated 1st-Party Downloads:** Investigate and implement automated download fallbacks for 1st-party Steinberg components (SDA, MediaBay) if they are missing from the `installers/` directory.
    *   [ ] **Automate MediaBay Update:** Currently stubbed.
*   [ ] **Reverse engineer the download assistant:** Create a Torquio download assistant that performs essentially the same functions as the Steinberg Download Assistant. This would require a bit of work keeping up with updates manually for the developers, but it would allow Torquio to install all Dorico components WITHOUT requiring the user sign in to the download assistant. We can include the download assistant in the install, and any installs we do perform, it would be nice if they were backwards-compatible/detected by the SDA so that the SDA could update them if the user chose. Essentially, a drop-in fully cross-compatible alternative whose sole function is to not require the user to have to sign in to a download app (meaning, the entire install process can run start to finish without any user intervention. They install grab Torquio, hit "install everything," and when it's done 15-30 minutes later, it's just ready to be used; activate your license using the activation manager and you're off to the races).
*   [ ] **NotePerformer UI:** Fix graphical glitches in the NotePerformer VST window. (Determine if this is still an issue under the current custom Wine build). Update: it is indeed still an issue; see below.
*   [ ] **"Edit Instrument"** Attempting to edit a VST instrument from within Play mode causes a crash/hang/failure. Investigate.
    *   [ ] **Create placeholder fix:** Implement DirectComposition Virtual Surfaces in Custom Wine
*   [ ] **NotePerformer Splash Screen Icon (Low Priority):** When NotePerformer briefly launches its splash screen, it lacks an icon in the Wayland overview/dash. This can likely be solved via the same icon/StartupWMClass extraction we used for the main apps. We need to get the hardcoded path of the NotePerformer exe, extract the icon, and assign it to a hidden .desktop file.
*   [ ] **Refactor in python:** For better legibility and maintainability.
*   [ ] **Create Flatpak GUI app:** Create graphical frontend for Torquio, distribute via Flathub.
*   [ ] **Distribute pre-built Docker container:** Build custom WINE branch on container, package it up, and distribute via ghcr (meaning the install would be able to skip that part, saving 15-30 minutes of install time).
*   [ ] **Eventually switch to Wine Wayland driver:** Once it is no longer buggy and has client side decorations implemented for GNOME. This makes moot a number of currently implemented workarounds/QOL features.
*   [ ] **Create Steam Deck controller layout:** Dorico via Torquio is Steam Deck compatible, but no controller layout exists for it, nor do any pre-existing generic templates suffice.
    *   [ ] **Run in fullscreen when gamescope is detected:** When running Dorico on Steam Deck (which uses gamescope), Dorico does not fill the screen. Inside the Dorico menu, switching to full screen fixes this, but it would be nice if this was automatic, if it's even possible, given that it's inside a Dorico menu and not, e.g., a WINE or Linux setting. 
*   [ ] **Add log exporter to Torquio:** A simple log zipper command in the torquio menus would be helpful (if a user wants to zip up the logs and attach it to a bug/issue, including WINE issues)
*   [ ] **Add an "update" button:** Add an "update Torquio" option to the menu. It would perform a git pull and then refresh launchers and so forth. That *should* be sufficient?
*   [ ] **See if you can't figure out why the SAM always signs the user out:** The SDA stays logged in between restarts (app restarts). The SAM requires the user to log in every single time. Not so on Windows. See if this can be remediated. Not tremendously high priority, because it works otherwise.
*   [ ] **GNOME / Adwaita Theming:** (Probably moot/not worth it/not possible) Investigate applying a Windows `.msstyles` theme to make Wine scrollbars and menus match GNOME/Adwaita natively. Explore having this run automatically if GNOME is detected. Consider doing the same for KDE, or just leaving it for KDE and all other DEs.

## Done
*(Move completed epics and tasks here for historical record)*

### Assorted
*   [x] **High-DPI / 4K Scaling:** Wine isn't scaling automatically on one particular 4K 28" screen (not sure about other 4K screens). We need to investigate Wine DPI registry keys or a dynamic DPI switcher alias. ALSO, new discovery: turning off xwayland scaling sizes the app correctly, but things are blurry, so what probably needs to happen is that anytime you start the app, the launcher checks if that's off, if off, turns it on, then it checks the dpi of the monitor and sets the wine dpi settings accordingly. Closing it should set everything back. -- Extra info/context: xwayland-native-scaling being turned off seems to fix this but also seems to cause blurriness. Ideally, we could have one solution that, at application launch, checks the monitor, its actual size and/or actual/recommended DPI, and whatever else, and automatically sets some settings just for Dorico. This means if a user ferries their 1080p laptop back and forth between a 4k dock, every launch will launch at the right resolution. Additionally, if it's possible to monitor what screen Dorico is on at any given moment and adjust the DPI accordingly on the fly, that would be even better, assuming it's possible.  
*   [x] **VSTAudioEngine6.exe Crash:** The audio engine crashes cleanly upon closing Dorico. This does not prevent proper function of the application; it's just ugly/annoying. Need to investigate if this is a Pipewire/ASIO routing issue or a Wine teardown bug.
*   [x] **Visual Glitches / GE-Proton Experiment:** The current `zhiyi/wine` build has transparent text in SDA and font ugliness. Create an experimental Git branch to try patching `dcomp` directly onto an *optimal* version of GE-Proton (known working verison of GE Proton without the visual glitches: GE Proton 10.33, but we probably want to test against either GE Proton current, GE Proton rc, or whatever GE Proton matches zhiyi/wine).
*   [x] **User Configuration Sync:** Create scripts to automate the backup/export and restoration of user key commands (`keycommands*.json`) and other critical preference files.
*   [x] **System-Wide Logging:** Implement a structured logging framework (e.g., redirecting stdout/stderr to `~/.local/state/torquio/logs/`) to provide users with a "debug bundle" they can share when hitting issues.
*   [x] **"License Eater" Bug:** On prior attempts in Bottles, a (assumed) hardware fingerprinting issue is causing licenses to disappear. Determine if the issue exists under our current method, and, if so, figure out a strategy for maintaining hardware fingerprint (if that is the problem). --Verdict: it was likely a Bottles issue. Not present under our current method.

### Epic: The Master Installer Wrapper (User Experience)
**Context:** Assuming Steinberg legal does not allow pre-packaged distribution, the end-user will need to provide their own `.exe` and `.zip` installers. We must not force Linux novices to use `git clone` or run multiple shell scripts. We need a single-command `curl | bash` installation experience.

#### Subtasks: Missing Component Scripts
We currently have `install_noteperformer.sh`, but we lack dedicated automation scripts for the core Steinberg components. Before we can build the master wrapper, we must build and test:
*   [x] **`install_sda.sh`**:
    *   Must use a generalized glob pattern (e.g., `Steinberg_Download_Assistant_*_Installer_win.exe`) to find the user-provided installer regardless of the version number they downloaded.
    *   Must handle the execution inside the container prefix.
*   [x] **`install_mediabay.sh`**:
    *   Move the unzip logic currently inside `setup_prefix.sh` into this dedicated script. It should look for the user-provided `.zip` inside the designated `installers/` directory rather than the repo root.
    *   After unzipping, the script must perform a **recursive cleanup** of blocked files (e.g., `preinstall.ps1`) within the extracted directory to prevent "Not Trusted" error code 231.
    *   After cleanup, navigate into the versioned subfolder and execute `wine Setup.exe`.
*   [x] **`update_mediabay.sh` (or CLI Updater Mode):** (Stubbed, awaiting refinement)
    *   SDA attempts to update MediaBay but fails due to the `preinstall.ps1` block (Error 231). We need to refactor `install_mediabay.sh` and/or the SDA's launcher (.desktop file or shell script) to handle subsequent updates (e.g., pre-emptively manually checking for updates prior to and outside of the SDA running; if an update is found, we automatically download the installer (which may be a feature we add in the future anyways), clean it, and finally run the new installer ALL BEFORE running the SDA).

### Epic: The CLI Refactor & Compatibility Polish
**Context:** The codebase has been rebranded from `valerio` to `torquio`, replacing the simple installer wrapper with a full-featured CLI interface (`torquio`) backed by a user configuration profile. We will also incorporate key compatibility bug remedies (network printing, keyboard auto-repeat lag, and transient modal window focus loss) directly into our defined sprint.

#### Subtasks: Core Rebranding & Prefix Setup
*   [x] **Common Variables & Renaming**:
    *   Rename all settings inside `scripts/common.sh` from `valerio` to `torquio` (e.g. `TORQUIO_CONTAINER_NAME="torquio-env"`, XDG data/cache paths).
    *   Rename host wrapper scripts in `scripts/3-runtime_handlers/` to `torquio-dorico`, `torquio-sam`, and `torquio-sda-handler` and install them to `~/.local/bin/` as clean terminal commands.
    *   Rebrand all launchers, stubs, and icon templates to use the `torquio` namespace.
*   [x] **Move master install script**:
    *   Relocate the master `install.sh` from the repository root to `scripts/install.sh`. It now lives in the same directory level as `cleanup.sh`, acting as sibling controllers called by the user-facing `torquio` CLI app.

#### Subtasks: CLI App Interface & Pre-Installation Setup Prompts
*   [x] **The `torquio` CLI Executable**:
    *   Replace `install.sh` in the repository root with the main `torquio` CLI utility. It must support clean ASCII art headers and flag-driven actions.
    *   **Interactive Menu + Flags (Hybrid Layout)**: Running `torquio` without arguments launches an interactive text menu. Passing flags (e.g. `--install`) bypasses the menu for scripting.
    *   Supported flags:
        - `-i`, `--install`: Run clean container/prefix setup.
        - `-r`, `--uninstall` ("remove"): Complete host/container environment purge.
        - `-f`, `--fix-icons`: Rebuild and refresh host desktop icons/launchers.
        - `-g`, `--graphics`: Spawns interactive graphics/scaling configuration toggles.
        - `-s`, `--status`: Display container/prefix verification stats and active preferences in a single unified dashboard.
        - `-u`, `--update`: Update MediaBay (requires work to be completed on update_mediabay.sh)
        - `-w`, `--winecfg`: Launch the prefix's `winecfg` in the container.
        - `-d`, `--map_folder`: Map a local folder into the prefix as a network drive.
        - `-k`, `--import_key_commands`: Import a key commands json or zip backup.
        - `-x`, `--export_key_commands`: Export key commands to a zip archive.
*   [x] **Pre-Installation Setup Prompts**:
    *   Modify the installation process to execute a quick setup interview *before* printing the manifest and installing:
        1. **Scaling Prompts**: Ask if Torquio should automatically manage display scaling and DPI. If yes, save `auto_scale_mutter=true` and `auto_dpi_detect=true` in `config.json`. If no, fall back to standard `96` (or pre-existing user DPI).

#### Subtasks: Profile Preferences Engine & Self-Healing Scaling Trap
*   [x] **Interactive Configuration Profile**:
    *   Deploy a JSON config file on the host at `~/.config/torquio/config.json` with toggles for:
        *   `auto_scale_mutter` (boolean, default false): Dynamic scaling override. (sets the xwayland-scaling-factor to 1 via the "self-healing xwayland scaling trap" defined below).
        *   `auto_dpi_detect` (boolean, default true): Dynamic monitor DPI detection.
        *   `manual_dpi` (integer, default 96): Manual DPI fallback.
        *   `original_scale_factor` (string/float, empty on fresh setup): Saves the host's active scaling factor before Torquio overrides it, to safely restore on uninstallation.
*   [x] **Self-Healing XWayland Scaling Trap**:
    *   Implement the GSettings scaling factor override inside the wrapper launchers. On startup, if `auto_scale_mutter` is active under GNOME, set `xwayland-scaling-factor` to `1.0` dynamically. Use a host-side shell `trap` to cleanly restore the user's original factor when the app shuts down.
*   [x] **Auto-DPI Monitor Resolution Detection**:
    *   If `auto_dpi_detect` is active, query display scale factor via host X11/Wayland variables on boot, calculate the optimal target Wine DPI, and dynamically overwrite the prefix registry's `LogPixels` setting.
*   [x] **Uninstallation Host Restore Prompt**:
    *   During `torquio --uninstall`, if Torquio was configured to manage display scaling, read the `original_scale_factor` from `config.json` and prompt the user to automatically restore their host environment to its original scale.

#### Subtasks: Compatibility Polish & Bug Remedies
*   [x] **Keyboard Focus Loss Mitigation (Modal Windows - Default Baseline)**:
    *   Always configure the prefix registry by writing the string value `FocusOnClick="Y"` to `HKCU\Software\Wine\X11 Driver` during setup. This forces active window focus acquisition upon mouse clicks, eliminating the GNOME Overview workaround when sub-dialogs close. Done automatically as a default baseline without requiring a config toggle.
*   [x] **CUPS Printer Discoverability**:
    *   Ensure the printing spooler bridge is functional by adding `libcups2` (64-bit) and `libcups2:i386` (32-bit WoW64 support) packages to the container package dependencies (`build_wine.sh` or automated apt installer).
*   [x] **Keyboard Auto-Repeat Lag Bug (Dual-Approach)**:
    *   Address rapid-fire, delayed inputs when holding keys under XWayland/Wine. Explore both pathways to find the most stable solution for Dorico:
        1. X11 Event Overrides: Setting `xset r rate` repeat rate overrides inside the container shell before launching the binaries.
        2. Wine Registry Input Tuning: Customizing key repeat delay/speed settings in `HKCU\Control Panel\Accessibility\Keyboard Response` inside the prefix registry.

#### Subtasks: Advanced User Utility Integrations
*   [x] **Positional & Graphical Folder Mapping (`-d`, `--map_folder`)**:
    *   **Positional Mode**: If parameters are passed (e.g. `--map_folder /path/to/folder e:`), directly create a symlink to `E:\` inside the prefix's `dosdevices/`.
    *   **Interactive Mode**: If no path is provided:
        1. Query host system for `zenity` (GNOME) or `kdialog` (KDE) and spawn a native graphical folder selector. Fall back to standard shell prompts if missing.
        2. Loop through `dosdevices/` starting from `d:` to automatically identify and assign the **first available drive letter**.
*   [x] **Multi-Language Key Command Export/Import (`-x` / `-k`)**:
    *   **Export (`-x`)**:
        1. Scan the Dorico prefix AppData folder for any files matching `keycommands_*.json`.
        2. Compress all matching profiles into a single archive on the host: `~/Downloads/torquio_keycommands_backup.zip`.
    *   **Import (`-k`)**:
        1. Scan `~/Downloads/` (dynamic XDG path) for matching `torquio_keycommands_backup.zip` or individual `keycommands_*.json` files.
        2. *Single Match*: If exactly one backup exists, import it immediately (decompressing the zip if necessary).
        3. *Multiple Matches*: Present a clean interactive prompt listing discovered items, plus a `[Browse...]` option.
        4. *No Matches (or Manual Search)*: Fall back to host-side `zenity` / `kdialog` file select GUI to let the user browse for their backup file.

### Subtasks: The "one-click" Bootstrapper (`install.sh`)
*   [x] **The Curl Command:** Create a single terminal command (e.g., `curl -sL ... | bash`) that users copy/paste from the GitHub README to download the installer framework.
*   [x] **Prerequisite Checks:** Script must check for `distrobox` (or `distroshelf`) and `docker`/`podman` (prompting the user to install them via Flatpak/system packages if missing). If missing, halt and print clear instructions to install them.
*   [x] **Asset Validation:** Ensure an `installers/` directory exists and prompt the user to drop their `.exe` files into it before continuing.
*   [x] **Execution Chain:** Sequentially call `build_wine.sh` -> `setup_prefix.sh` -> `install_sda.sh` -> `install_mediabay.sh` -> `install_noteperformer.sh`.
*   [x] **Final Integration:** Automatically register the `.desktop` stubs and MIME types.
*   [x] **Cleanup/Uninstaller Script (`scripts/cleanup.sh`):** Create a robust script to wipe the environment (container, XDG share/cache dirs, and host integrations) to allow for clean re-installs or uninstallation.

### Epic: Engine Dependency Automation (libicu)
**Context:** Wine requires native ICU support for core Unicode translation, and Steinberg apps require Windows-side ICU binaries within the prefix.
*   [x] **Native Dependencies:** Added `winetricks`, `unzip`, and `cabextract` to `scripts/1-build/build_wine.sh`.
*   [x] **Prefix Dependencies:** Automated `wine-icu-72.1` download and silent MSI installation in `scripts/2-install/setup_prefix.sh`.
*   [x] **Cleanup:** Delete `scripts/1-build/TO_BE_DELETED_rebuild_wine_icu.sh` once the above are verified working in a fresh build.

### Epic: Documentation & Repository Polish
**Context:** Prepare the repository for public consumption and preserve AI agent context.
*   [x] **Update Main README:** Refactor `README.md` to be strictly user-facing (What is it, prerequisites, installation). Move developer/architectural deep-dives to `docs/ARCHITECTURE.md`.
*   [x] **Add Standard Open Source Docs:** Create `CONTRIBUTING.md` and `LICENSE` files.


### Epic: UX/UI Desktop Integration
**Context:** Distrobox auto-exports `.desktop` files with proper icons, conflicting with our custom manual ones which handle the `net-steinberg-sam://` URI schemes. We need to merge the "Nice Icon" with the "Functional Link Handler" and establish actual scripted functionality. There may be other good stuff in the exported .desktop files that we want in ours.

#### Subtasks: .desktop File Merging
*   [x] **Suppress winemenubuilder:** Wine automatically creates `.desktop` links for Windows applications and file extensions (e.g., in `~/.local/share/applications/wine/Programs/`). This pollutes the host environment. We need to export `WINEDLLOVERRIDES="winemenubuilder.exe=d"` in our installation scripts so Wine stops spamming the host's app menu. *Note: When we write the cleanup script for these, it must be carefully targeted (e.g., only deleting Steinberg/Dorico specific files) so we don't accidentally wipe a user's desktop files from other non-Torquio Wine prefixes.*
*   [x] Use the current "messy" state of the host machine as a diagnostic baseline.
*   [x] The stubs in `desktop_stubs/` currently lack `Icon=` paths. 
*   [x] Need a post-install script that runs `distrobox-export --app` for SDA, SAM, and Dorico. (Implemented a cleaner, Distrobox-independent solution via surgical `wrestool` extraction).
*   [x] Extract the generated `Icon=` lines from the Distrobox-exported files located in the host's `~/.local/share/applications/`. (Bypassed via surgical extraction).
*   [x] Inject those Icon paths into our custom URI-handler stubs and overwrite the Distrobox ones, ensuring the user gets one clean icon that launches the app *and* handles the login links.
*   [x] **MIME/Protocol Handler Priority:** Resolve the conflict where GNOME prompts the user to choose between the "SDA" and the "SDA Handler" when clicking login links. Ensure our handler is the default for `net-steinberg-*` protocols (OR, preferably, the SDA itself and the SDA handler need to be the same thing somehow so the choice couldn't even exist in the first place--our handlers are essentially hacks that we overlay on top of a legitimate Dorico install; we want to get as close to normal native function as possible). (Resolved by unifying into a single stub per application).
*   [x] Investigate: currently, with both our custom .desktop files and the Distrobox-exported ones, GNOME/Wayland are using the icons from the Distrobox-exported file for displaying running apps in the dash and overview (and in the app picker lists for running unknown file types). We need to see if that still occurs when there is only our correct one, and if so, we need to figure out how to fully integrate ours into these system functions. (Resolved via `StartupWMClass` metadata).

### File Associations & Opening Files
*   [x] **File assocations:** Clicking on Dorico files in the file explorer brings up a "Could Not Display "FILENAME.dorico" There is no app installed for "Dorico Project" files. (Resolved by properly escaping execution scripts, exporting exact MIME types, and explicitly setting `mimeapps.list`).
*   [x] **Opening Files** Clicking on Dorico files from the file explorer does nothing. Dorico (with the proper icon) is set as the program to open the files, but that isn't the Dorico we use to launch Dorico, so that's likely the issue. Investigate. (Resolved via correct script proxying of the Windows path).

### Production Path Refactoring
*   [x] **Production Path Refactoring:** Transition from isolated development paths (`~/dev/...`) to standard production paths.
*   [x] **Production Path Refactoring:** Transition from isolated development paths (`~/dev/...`) to standard production paths.
    *   Removed hardcoded `$HOME/dev/steinberg-on-linux` references in `build_wine.sh` and `setup_prefix.sh` and replaced them with dynamic workspace variables and XDG-compliant paths.
    *   Scripts now dynamically generate the Wine prefix in a user-agnostic XDG location (`~/.local/share/torquio/prefix`).
    *   Added `scripts/common.sh` for shared environment variables.
