# Steinberg Dorico on Linux - Active Blueprint (Container Method)

## The "jgke" Container Method (Current Work-in-Progress)
This is the active roadmap for building a reproducible, high-performance Steinberg environment on an immutable host using Distrobox and a custom-compiled Wine.

### Current Base Environment
*   **Container Host:** Distrobox (Ubuntu 24.04).
*   **Engine:** Docker.
*   **Custom Wine Build:** `zhiyi/wine` branch `bug-23698-react-native-20251217`.
    *   *Why:* Includes DirectComposition (`dcomp`) stubs required by Dorico 6.
    *   *Build Specifics:* Compiled with native `libicu-dev` support.
*   **Prefix Config:** Windows 10 (via Winetricks).
*   **Core Dependencies:** `d3dx9`, `msls31`, `allfonts`, `d3dcompiler_43`, `d3dcompiler_47`, `vcrun2019`, `dotnet48`, `wine-icu` (manual MSI).

### Permanent Infrastructure & Scripting
These scripts are currently sitting in the repository root and serve to preserve the environment variables and launch logic across reboots and different machines.

*   **`build_wine.sh`:** Automates the fetching of build-deps and the dual-architecture (32/64-bit) Wine compilation.
*   **`setup_prefix.sh`:** Automates the creation of the Wine prefix and the installation of initial Winetricks dependencies.
*   **`dorico.sh`:** Handles launching Dorico 6 with the correct `WINEPREFIX` and `PATH` inside the container.
*   **`sam.sh`:** Handles the Activation Manager, including the handoff logic for `net-steinberg-sam://` URL tokens using the `--redirect` flag.
*   **`install_noteperformer.sh`:** A generalized installer script that uses glob patterns (`NotePerformer-Installer-*.exe`) to handle the customer-specific personalized filenames used by NotePerformer.

## Installed Components & Working Features
*   **NotePerformer 5.1.2:** Successfully installed and verified running in Dorico. (Manual installation confirmed working under the `dcomp` Wine build).

## To-Do List (Tech Debt & Polish)
*   **The Master Installer Wrapper (User Experience):** Assuming Steinberg legal does not allow pre-packaged distribution, the end-user will need to provide their own `.exe` and `.zip` installers. We must not force Linux novices to use `git clone` or run multiple shell scripts. We need to architect a "one-click" bootstrapper:
    1. **The Curl Command:** A single terminal command (e.g., `curl -sL ... | bash`) that users copy/paste from the GitHub README to download the installer framework.
    2. **Prerequisite Check:** The script must check if Distrobox/Distroshelf and Docker/Podman are installed (prompting the user to install them via Flatpak/system packages if missing).
    3. **The Wrapper:** Once prerequisites are met, the script detects the provided Steinberg installer files, bootstraps the container prefix, sequentially executes the software installers, and automatically registers the `.desktop` stubs and MIME types.
*   **Production Path Refactoring:** Transition from isolated development paths (`~/dev/...`) to standard production paths. Scripts must be updated to dynamically generate the Wine prefix in a user-agnostic XDG location (e.g., `~/.local/share/wineprefixes/dorico`) rather than the repo directory.
*   **High-DPI / 4K Scaling:** Wine isn't scaling automatically on one particular 4K 28" screen (not sure about other 4K screens). We need to investigate Wine DPI registry keys or a dynamic DPI switcher alias.
*   **VSTAudioEngine6.exe Crash:** The audio engine crashes cleanly upon closing Dorico. This does not prevent proper function of the application; it's just ugly/annoying. Need to investigate if this is a Pipewire/ASIO routing issue or a Wine teardown bug.
*   **Visual Glitches / GE-Proton Experiment:** The current `zhiyi/wine` build has transparent text in SDA and font ugliness. Create an experimental Git branch to try patching `dcomp` directly onto an *optimal* version of GE-Proton (known working verison of GE Proton without the visual glitches: GE Proton 10.33, but we probably want to test against either GE Proton current, GE Proton rc, or whatever GE Proton matches zhiyi/wine).
*   **GNOME / Adwaita Theming:** Investigate applying a Windows `.msstyles` theme to make Wine scrollbars and menus match GNOME/Adwaita natively. Explore having this run automatically if GNOME is detected. Consider doing the same for KDE, or just leaving it for KDE and all other DEs.
*   **Desktop Shortcut Cleanup (UX/UI):** Distrobox auto-exported `.desktop` files with proper icons, conflicting with our custom manual ones. Use the current "messy" state of this machine as a diagnostic baseline to merge the "Nice Icon" with the "Functional Link Handler" and establish actual scripted functionality. *Must also recover `steinberg-sda-handler.sh` from the host system and commit it, along with `.desktop` file templates, directly to the repository.*
*   **Consolidate Build Artifacts:** We currently have a `rebuild_wine_icu.sh` script. Because we have since added `libicu-dev` to the primary `build_wine.sh` script, this rebuild script is obsolete. Verify the primary build works cleanly, then delete the rebuild script.
*   **Automate Wine-ICU Installation:** Add the silent download and installation of the `72.1` MSI to the build script.
*   **Version Manifest Generation:** Programmatically extract and record the exact version numbers of every piece of installed Steinberg software to create a reproducible manifest.
*   **"License Eater" Bug:** On prior attempts in Bottles, a (assumed) hardware fingerprinting issue is causing licenses to disappear. Determine if the issue exists under our current method, and, if so, figure out a strategy for maintaining hardware fingerprint (if that is the problem).

*   **NotePerformer UI:** Fix graphical glitches in the NotePerformer VST window. (Determine if this is still an issue under the current custom Wine build).

## Reproducibility Artifacts (Hashes)
*   **Wine Repository (`zhiyi/wine`):** Commit `ae88a705b5aa544cc60153d48c1ca8849f32ee14`.
*   **Winetricks:** Version `20260125-next` (SHA256: `8f07319f32e96a7ad92f786bf8ee2e00d3c65f82debd33b6884e681b825ae67a`).
