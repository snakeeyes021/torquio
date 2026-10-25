# Project Backlog

This document is the single source of truth for all tasks, bugs, and enhancements.

## Defined Work (Sprint)
This section tracks epics that have been broken down into concrete, actionable subtasks.

*   [ ] **Release plan:**
    *   [x] **v0.5.0:** Plug-in window icons, version manifest generation and the prebuilt container image (released 2026-10-24).
    *   [ ] **v0.6.0:** Refactor in Python (epic below).
    *   [ ] **v0.7.0:** Flatpak GUI app on Flathub.

### Epic: Torquio in Python (v0.6.0)
Rewrite the host-side Bash in standard-library Python (3.9+) with no user-visible change, as a core library plus a thin CLI that the v0.7.0 GUI can reuse. The full plan (layout, contracts that must never break, parity testing, risks) is in `docs/REFACTOR.md`. Each stage is its own branch, tested for parity and merged to develop on its own; the Bash `torquio` stays the entry point until stage 7.

*   [ ] **Stage 0, foundation:** `lib/torquio/` skeleton with `paths`, `config` (replacing the Python one-liners in `common.sh`), `ui` and `run`; the three existing Python scripts moved into the package (old paths kept as wrappers); Python version check; unit-test and parity harness; CI workflow.
*   [ ] **Stage 1, read-only screens:** dashboard, graphics diagnostics, header, help text, manifest.
*   [ ] **Stage 2, maintenance:** Wine Tools menu and actions, GPU setup and chooser, ntsync, key commands, folder mappings, custom exe, Settings, update check.
*   [ ] **Stage 3, engine and container:** `replace_container`, engine update/rebuild, `engine_outdated`, machine identity, self-update and `--post-update`.
*   [ ] **Stage 4, uninstall:** `cleanup.sh`.
*   [ ] **Stage 5, install:** `install.sh` and the host-side `install_*.sh` helpers, launcher and icon installation.
*   [ ] **Stage 6, launchers:** `torquio-dorico`, `torquio-sam`, `torquio-sda-handler`, graphics automation; the Dorico runner as a template file.
*   [ ] **Stage 7, entry point:** menu loop and flag parsing; `torquio` becomes a small Python entry point; dead Bash removed; docs updated. Full regression pass, then release v0.6.0.


## Undefined Work (Backlog)
This section tracks high-level goals and ideas that have not yet been broken down into concrete subtasks.

*   [ ] **Cantai (work in progress):** Cantai is functional: the installer detects its download and installs it silently (`scripts/2-install/install_cantai.sh`), Dorico gets the `Auto & Cantai` playback template automatically, and it loads, activates, renders (on the GPU where possible) and opens its editor in every instance. Remaining:
    *   [x] **Unreliable audio (placeholder tone, missing parts):** Fixed by Wine patch 0010. Cantai's local renderer (`cantai.exe`, a Python/onnxruntime server on `127.0.0.1:38471`) runs `wmic csproduct get UUID` on every `/health` request; under Wine each run started a process (0.35-0.5 s idle, seconds while rendering), and the plug-in's watchdog treated the slow answers as a hang, restarted the renderer and abandoned the render. Patch 0010 answers exactly that command inside `CreateProcessInternalW` without starting a process (byte-identical output, same SMBIOS UUID as Wine's wmic, so the license fingerprint is unchanged). Tested 2026-10-23: 6 of 6 fresh 4-part renders finished with no renderer restarts (slowest `/health` 0.52 s, was up to 6.4 s), and the played-back audio is the choir, not the placeholder.
    *   [ ] **Edits made while the renderer is starting are dropped:** If the score changes within a few seconds of the renderer (re)starting, Cantai never renders that change until the next edit. The first render of a freshly started renderer can also delay `/health` (up to ~7 s during model loading); the plug-in then briefly launches a second renderer, but the render survived in testing. Rare now that the watchdog no longer restarts the renderer.
    *   [x] **Rendering is CPU-only and slow-ish:** Now uses the GPU for 2 of its 8 model stages (see "GPU for AI plug-ins" below); ~2x faster on an NVIDIA laptop GPU. Only tested on Intel Iris Xe (Mesa ANV) and NVIDIA (proprietary 615); other drivers are unverified, and wrong output would be silent (the `ai_gpu` setting can turn it off).
    *   *Notes:* the renderer stays running ~2 minutes after Dorico quits (Cantai's idle timeout, same without patch 0010). Wine derives the Windows system UUID (which Cantai's license is tied to) from the container's `/var/lib/dbus/machine-id`, which used to be random per container, so Cantai saw a new computer whenever the container was re-created. New containers now get an ID derived from the host's machine ID (hashed), and `replace_container` carries the old one over (`scripts/1-build/container_gpu_setup.sh`). Installs made before that keep their own random ID, which would be lost if the container were ever deleted outside Torquio; the dashboard flags it and `torquio --fix-identity` (also offered after updates) switches to the derived ID once the user has deactivated plug-ins such as Cantai.
    *   [x] **Unattended install:** The installer runs Cantai's Inno Setup silently (falling back to the wizard if that fails) and imports the playback template on the first Dorico launch.
*   [ ] **Consolidate the DirectComposition patches:** Patches 0004, 0005, 0007 and 0009 all modify `dlls/dcomp/device.c` and stack in order. Fold them together; this doesn't have to wait for a rebase onto a newer `zhiyi/wine` commit. First check whether 0008 (hide layered windows until drawn) makes 0005's opacity-hide redundant.
*   [ ] **HALion Sonic editor exception dump:** On a fresh install, with HALion Sonic's window open, the audio engine recorded a caught access violation (null pointer + 0x10) as a crash dump, then kept running and exited normally. Wine left the dump's module list empty, so the faulting DLL is unknown. Reproduce and identify.
*   [ ] **Splash screen black flash:** Not verified since the dropdown fixes; the splash doesn't use the DirectComposition path those fixes cover.

*   [ ] **Update Torquio-managed components as part of "Update Torquio":** Some components only Torquio can keep current because their normal Windows update path doesn't work under Wine: MediaBay (the SDA's own update fails with error 231, see below; `scripts/2-install/update_mediabay.sh` is a placeholder) and the fixed WebView2 runtime installed for Cantai (`install_webview2.sh`; Windows updates it in the background, here nothing does). After updating itself, `torquio -u` should check these and update them, so users never need to know which part needs updating. Steinberg apps stay with the SDA and third-party plug-ins with their vendors' installers. Do the MediaBay and WebView2 updates together.
    *   [ ] **Automate MediaBay Update:** Currently stubbed. On a fresh install the SDA downloads the latest MediaBay (1.4.10 as of 2026-10-22) and runs it through the Steinberg Install Assistant, which fails with error 231: `preinstall.ps1: not trusted` (Setup.exe verifies the script's Authenticode signature, which Wine can't verify for PowerShell scripts). The SDA then opens Steinberg's "component update error" page, and the older MediaBay from the user's zip stays installed. The script only stops a running MediaBay server before an update; deleting it (as `install_mediabay.sh` does) is safe, and Setup.exe also installs `LibraryManager.msi` and registers bundled content, so keep using Setup.exe rather than `MediaBay.msi`. A watcher can't fix the SDA's own attempt: it installs straight from inside the downloaded zip ~0.1 s after the download completes. Plan: install the latest MediaBay before the SDA first runs, so it never attempts the update. Blocked on finding a stable public download URL (Steinberg's download pages were offline at the time).
*   [ ] **Automated 1st-Party Downloads:** Investigate and implement automated download fallbacks for 1st-party Steinberg components (SDA, MediaBay) if they are missing from the `installers/` directory. A stable public MediaBay URL would also unblock "Automate MediaBay Update" above.
*   [ ] **Reverse engineer the download assistant:** Create a Torquio download assistant that performs essentially the same functions as the Steinberg Download Assistant. This would require a bit of work keeping up with updates manually for the developers, but it would allow Torquio to install all Dorico components WITHOUT requiring the user sign in to the download assistant. We can include the download assistant in the install, and any installs we do perform, it would be nice if they were backwards-compatible/detected by the SDA so that the SDA could update them if the user chose. Essentially, a drop-in fully cross-compatible alternative whose sole function is to not require the user to have to sign in to a download app (meaning, the entire install process can run start to finish without any user intervention. They install grab Torquio, hit "install everything," and when it's done 15-30 minutes later, it's just ready to be used; activate your license using the activation manager and you're off to the races).
*   [ ] **Create Flatpak GUI app:** Create graphical frontend for Torquio, distribute via Flathub.
*   [ ] **Eventually switch to Wine Wayland driver:** Once it is no longer buggy and has client side decorations implemented for GNOME. This makes moot a number of currently implemented workarounds/QOL features.
*   [ ] **Pre-install distrobox's base packages in the image (low priority):** The first start of every new container spends about a minute in distrobox's "Installing basic packages..." (`apt-get update` plus ~50 packages: sudo, locales, bash-completion, man-db, xauth, ...; see `setup_apt` in `distrobox-init`). Installing that list in the Containerfile would make it nearly instant. Changes the build files, so it ships with the next engine image.
*   [ ] **Create Steam Deck controller layout:** Dorico via Torquio is Steam Deck compatible, but no controller layout exists for it, nor do any pre-existing generic templates suffice.
    *   [ ] **Run in fullscreen when gamescope is detected:** When running Dorico on Steam Deck (which uses gamescope), Dorico does not fill the screen. Inside the Dorico menu, switching to full screen fixes this, but it would be nice if this was automatic, if it's even possible, given that it's inside a Dorico menu and not, e.g., a WINE or Linux setting. 
*   [ ] **GNOME / Adwaita Theming:** (Probably moot/not worth it/not possible) Investigate applying a Windows `.msstyles` theme to make Wine scrollbars and menus match GNOME/Adwaita natively. Explore having this run automatically if GNOME is detected. Consider doing the same for KDE, or just leaving it for KDE and all other DEs.
*   [ ] **See if you can't figure out why the SAM always signs the user out:** The SDA stays logged in between restarts (app restarts). The SAM requires the user to log in every single time. Not so on Windows. See if this can be remediated. Not tremendously high priority, because it works otherwise.
    *   *Findings (2026-10-22):* Not a Wine storage bug. On sign-in the License Engine (`SteinbergLicenseEngine.exe`, started fresh with every Activation Manager session) writes the refresh token with `CredWriteW` (generic credential "Steinberg Activation Manager", ~1.5 KB, valid 30 days) and the access token to `AppData\Roaming\Steinberg\Activation Manager\Data\access.txt`. Wine stores and returns the credential intact (verified with a `CredReadW` test program). On the next start the engine reads `access.txt` and the credential, then logs "1.1 Format refresh token detecting -- resetting", deletes `access.txt`, and requires a new sign-in. What makes it classify the token as the old 1.1 format is internal to the engine (no credential attributes are used; `expiryinfo.txt` is only ever read, never written). Next step if revisited: disassemble the check around that log string. Licenses stay activated regardless; only the sign-in is lost.
*   [ ] **Cantai editor is white for several seconds before content appears:** Most of this is the embedded WebView2 (Chromium) starting up under Wine. No fix found yet.

## Done
*(Move completed epics and tasks here for historical record)*

### Assorted
*   [x] **Prebuilt container image:** `scripts/1-build/Containerfile` + `.github/workflows/container-image.yml` publish `ghcr.io/snakeeyes021/torquio-env:build-<tree hash of scripts/1-build>` (public; ~1.5 GB download, 4.8 GB unpacked; CI build ~75 min). The installer pulls the image matching its own build files and compiles only when there is none; engine updates pull the new image and swap the container (`replace_container`, keeping NVIDIA access and the machine ID). Verified 2026-10-24: Dorico, NotePerformer and Cantai from the image; a real update from a locally compiled container to the GHCR image and back, with Cantai staying activated throughout.
*   [x] **`rundll32` errors when Wine updates the prefix:** Every Wine engine change makes Wine update the prefix ("Wine is updating..." window), which re-registers `mscoree.dll` through `rundll32` (`wine.inf`), once 64-bit and once 32-bit. With Microsoft's .NET 4.8 installed, its `mscoree.dll` answers that with ".NET: This application could not be started" in a `rundll32.exe` dialog, twice; harmless (.NET's installer registered it already). Fixed with a per-program override that keeps .NET out of `rundll32` (`HKCU\Software\Wine\AppDefaults\rundll32.exe\DllOverrides`, `"*mscoree"=""`; the `*` matters, as `wine.inf` loads it by full path and the prefix's own override is `"*mscoree"="native"`). New prefixes get it in `setup_prefix.sh`; existing ones from `apply_prefix_settings` (after updating Torquio and before an engine update or rebuild, so it's in place before the prefix update). Verified on a copy of a real prefix: the update shows only Wine's own window.
*   [x] **Version Manifest Generation:** `torquio --manifest` (`scripts/version_manifest.py`) prints the "Build Environment Artifacts" and "Verified Application Versions" sections of a release entry. Applications come from the prefix's Uninstall registry keys (machine-wide and per-user; Steinberg's bundled components such as HALion Sonic are left out), extended to the full file version of their executables where that adds detail (e.g. Dorico `6.2.30` -> `6.2.30.6245`). The Wine commit and patches come from a build record `build_wine.sh` now writes to `/opt/wine-custom/share/torquio/build-info`, so they describe the installed engine rather than the repo; the manifest warns when they differ from the repo's (engine needs a rebuild), when the engine was built from uncommitted changes, and for engines built before the record existed. The log export includes the manifest.
*   [x] **Plug-in window icons (NotePerformer splash, instrument windows, Cantai):** Plug-in windows had no icon in the dash/overview. NotePerformer and Cantai have no process of their own: every plug-in window, including NotePerformer's splash, is created by Dorico's audio engine, and Wine gives all of a process's windows the same window class (`vstaudioengine6.exe`, confirmed with a window watcher on 2026-10-23). So they share one hidden "Dorico Audio Engine" launcher (`desktop_stubs/Dorico Audio Engine.desktop`) with the engine's own icon, extracted from `VSTAudioEngine6.exe`. Per-plug-in icons were rejected: they would need a helper to relabel another program's windows by title, misrepresenting what owns them.
*   [x] **High-DPI / 4K Scaling:** Wine isn't scaling automatically on one particular 4K 28" screen (not sure about other 4K screens). We need to investigate Wine DPI registry keys or a dynamic DPI switcher alias. ALSO, new discovery: turning off xwayland scaling sizes the app correctly, but things are blurry, so what probably needs to happen is that anytime you start the app, the launcher checks if that's off, if off, turns it on, then it checks the dpi of the monitor and sets the wine dpi settings accordingly. Closing it should set everything back. -- Extra info/context: xwayland-native-scaling being turned off seems to fix this but also seems to cause blurriness. Ideally, we could have one solution that, at application launch, checks the monitor, its actual size and/or actual/recommended DPI, and whatever else, and automatically sets some settings just for Dorico. This means if a user ferries their 1080p laptop back and forth between a 4k dock, every launch will launch at the right resolution. Additionally, if it's possible to monitor what screen Dorico is on at any given moment and adjust the DPI accordingly on the fly, that would be even better, assuming it's possible.  
    *   *Update (Active Research)*: Evaluated native Wayland drivers and determined that `winewayland.drv` introduces major window management regressions (missing titlebars, buggy snapping under GNOME). Confirmed the optimal scaling bypass is setting GNOME's `xwayland-scaling-factor` to `1` (which disables compositor overscaling and renders 1:1, a setting KDE Plasma already defaults to via "Apply scaling themselves"), and then scaling Dorico internally using Wine's DPI (e.g. 120 DPI). Investigating integrating a dynamic GSettings trap/wrapper in the launchers and an automated display DPI detection profile.
*   [x] **VSTAudioEngine6.exe Crash:** The audio engine crashes cleanly upon closing Dorico. This does not prevent proper function of the application; it's just ugly/annoying. Need to investigate if this is a Pipewire/ASIO routing issue or a Wine teardown bug.
*   [x] **Dropdown menus render blank / don't redraw ([#6](https://github.com/snakeeyes021/torquio/issues/6)):** Dorico's DirectComposition-rendered dropdowns went completely white from the second open onwards. Partially fixed in v0.3.5-alpha (dropdowns display their content on every open). Fully resolved on `fix/dcomp-dropdown-redraw` by Wine patches 0004-0009: dropdowns and tooltips redraw on hover/keyboard (Qt 6.10 needs a blocking `IDXGIOutput::WaitForVBlank`) and show the latest frame; no black flash or white corners; Windows 11 rounded corners; no flash on first open; nested menus work. The "missing scroller chevrons" are Dorico's design (a scroll indicator shown only while scrolling).
*   [x] **Dorico "Activate for playback" window is white:** When opening a second project (at least from a dragged MIDI import), the "Activate for playback" window renders completely white. (No longer reproduces as of the `fix/dcomp-dropdown-redraw` Wine patches.)
*   [x] **Add an "update" button:** Add an "update Torquio" option to the menu. It would perform a git pull and then refresh launchers and so forth. That *should* be sufficient? (Done: "Update Torquio" in both main menus and `torquio -u` fetch, list what's new, ask, fast-forward only (refusing if Torquio's files were changed locally), then re-run the updated script to refresh launchers, icons and prefix settings, and offer a Wine engine rebuild when `scripts/1-build/` changed. The MediaBay updater placeholder lost its `-u` flag; see "Update Torquio-managed components".)
*   [x] **Add log exporter to Torquio:** A simple log zipper command in the torquio menus would be helpful (if a user wants to zip up the logs and attach it to a bug/issue, including WINE issues) (Done: `torquio -l` / "Export Logs" in both main menus writes `~/Downloads/torquio-logs-<date>.zip` via `scripts/export_logs.py`: Torquio and launcher logs (including Wine's output), Dorico, audio engine, Activation Manager, Steinberg Runtime and Download Assistant logs, plus a system summary. Emails (and an email's first half where it appears as a folder name), the username, the computer name, sign-in tokens, the hardware ID and license/grant/product IDs are redacted by pattern; license data, registry files and crash dumps are never included.)
*   [x] **MIDI drag-and-drop opens new project instead of inserting onto current staff:** Dragging a MIDI file in does not drop it onto the currently selected staff; instead, it opens a new project. Investigate if this is default Dorico behavior, a setting/modifier requirement, or a Wine drag-and-drop/OLE integration quirk. (Assumed working as intended: dropping a MIDI file onto a track in Play mode imports it into the current project, which Dorico supports since 4.3.10; dropping it elsewhere opens it as a new project, and Dorico has no drop-onto-selected-staff feature. Use File > Import > MIDI to merge into existing flows.)
*   [x] **GPU for AI plug-ins (Cantai), including NVIDIA:** Cantai's renderer never used the GPU because Wine's dxcore was a stub: onnxruntime's DirectML provider skips adapters that don't report `DXCORE_ADAPTER_ATTRIBUTE_D3D12_GRAPHICS`. Wine patch 0011 reports the Direct3D 12 / compute / ML attributes, but only when the process uses a native d3d12 (DirectML on Wine's builtin d3d12 computes wrong results: Cantai's vocoder produced fixed tones). The Dorico launcher gives Cantai vkd3d-proton (`install_vkd3d_proton.sh`, pinned 3.0.1 + SHA-256; DLLs next to `Cantai.exe` plus a DLL override for that executable only) and sets `VKD3D_FILTER_DEVICE_NAME` to the strongest GPU from `vulkaninfo` (discrete of any brand, else integrated; setting `ai_gpu`: auto / off / a GPU name; menu Wine Tools > 13). NVIDIA needs the container created with `distrobox --nvidia` (new installs do it automatically; existing ones are offered a snapshot-and-recreate by Update Torquio / `torquio --setup-gpu`) plus `container_gpu_setup.sh`, because Distrobox's copied NVIDIA Vulkan JSONs name the host's library path (Fedora's `/usr/lib64/...`), which doesn't exist in Ubuntu. Results (fresh 4-part SATB, 2026-10-23): CPU 44-47 s, Intel Iris Xe 36-37 s, NVIDIA RTX 3080 Ti Laptop 20-24 s; output matches the CPU renders. Cantai puts 2 of its 8 model stages (acoustic, vocoder) on the GPU.
*   [x] **Uninstall license guard:** The uninstaller (and "Fresh Reinstallation") reads the Activation Manager's `activation.dat` (`scripts/steinberg_license_state.py`; activated licensed items carry a license token) and refuses to delete a prefix with activated Steinberg licenses unless the user types an explicit override; if the state can't be determined it asks for a typed confirmation. Verified against real deactivate/reactivate/sign-out cycles. Note: signing out of the Activation Manager deactivates all licenses.
*   [x] **Visual Glitches / GE-Proton Experiment:** The current `zhiyi/wine` build has transparent text in SDA and font ugliness. Create an experimental Git branch to try patching `dcomp` directly onto an *optimal* version of GE-Proton (known working verison of GE Proton without the visual glitches: GE Proton 10.33, but we probably want to test against either GE Proton current, GE Proton rc, or whatever GE Proton matches zhiyi/wine).
*   [x] **User Configuration Sync:** Create scripts to automate the backup/export and restoration of user key commands (`keycommands*.json`) and other critical preference files.
*   [x] **System-Wide Logging:** Implement a structured logging framework (e.g., redirecting stdout/stderr to `~/.local/state/torquio/logs/`) to provide users with a "debug bundle" they can share when hitting issues.
*   [x] **"License Eater" Bug:** On prior attempts in Bottles, a (assumed) hardware fingerprinting issue is causing licenses to disappear. Determine if the issue exists under our current method, and, if so, figure out a strategy for maintaining hardware fingerprint (if that is the problem). --Verdict: it was likely a Bottles issue. Not present under our current method.
*   [x] **NotePerformer UI:** Fix graphical glitches in the NotePerformer VST window. (Determine if this is still an issue under the current custom Wine build). Update: it is indeed still an issue; see below. (Resolved in v0.3.5-alpha by the DirectComposition patches.)
*   [x] **"Edit Instrument"** Attempting to edit a VST instrument from within Play mode causes a crash/hang/failure. Investigate. (Resolved in v0.3.5-alpha by the DirectComposition patches; works on a per-VST basis. NotePerformer works. Cantai's window opens as of `fix/dcomp-dropdown-redraw`; remaining Cantai work is tracked above.)
    *   [x] **Create placeholder fix:** Implement DirectComposition Virtual Surfaces in Custom Wine
*   [x] **Kernel Fast Sync (ntsync) ([#5](https://github.com/snakeeyes021/torquio/issues/5)):** The custom Wine build silently compiled out ntsync because the ubuntu:24.04 container's 6.8-series headers lack `linux/ntsync.h`, leaving every sync operation on the slow wineserver RPC path (Select All on a 23-page score took 108 s vs 6.2 s on Windows). Fixed in v0.3.5-alpha: `build_wine.sh` injects a vendored `ntsync.h` (falling back to host kernel headers) and re-enables the wineserver in-process ntsync device handle. The installer, `--enable-ntsync`, and the Wine menu load and persist the `ntsync` module; the status dashboard reports its state. Requires a 6.14+ host kernel.

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
    *   Removed hardcoded `$HOME/dev/steinberg-on-linux` references in `build_wine.sh` and `setup_prefix.sh` and replaced them with dynamic workspace variables and XDG-compliant paths.
    *   Scripts now dynamically generate the Wine prefix in a user-agnostic XDG location (`~/.local/share/torquio/prefix`).
    *   Added `scripts/common.sh` for shared environment variables.
