# Release Manifest & Version History

This document tracks known-good, tested "snapshots" of the entire system. It serves as a single source of truth for reproducibility, ensuring we know exactly which build environment artifacts and software versions successfully worked together at a given point in time.

---

## **Release v0.4.0-alpha (Dropdowns, Cantai on the GPU & Maintenance Tools)**
**Date:** 2026-10-23
**Status:** Alpha / Milestone

**Description:** Finished the DirectComposition work: dropdowns and tooltips now redraw, look and behave as on Windows. Cantai is functional end to end (installed silently with its playback template, editors, reliable rendering) and renders on the GPU, including NVIDIA GPUs. Added an uninstall license guard, a log exporter and self-updating. Verified with a from-scratch install on RedFoxOS, a Bazzite-based Fedora Atomic image (Intel Iris Xe + NVIDIA RTX 3080 Ti Laptop), and an upgrade of an existing install.

**Key Improvements:**
*   **Dropdowns & Popups (#6):** Wine patches 0004-0009: dropdowns and tooltips redraw on hover and keyboard input (Qt 6.10 needs a blocking `IDXGIOutput::WaitForVBlank`) and show the latest frame; no black flash or white corners; Windows 11 rounded corners; no flash on first open; nested menus work. Plug-in host text renders (Segoe UI aliased to Tahoma).
*   **Cantai:** Detected and installed silently with the other installers (WebView2 runtime provisioned for its editor); its "Auto & Cantai" playback template is added to Dorico automatically; per-user VST3 plug-ins are loaded; every editor window shows its content; Dorico no longer hangs on exit. Wine patch 0010 stops Cantai's renderer from being restarted mid-render (its per-request `wmic` call is answered without starting a process), which caused missing parts and the placeholder tone.
*   **GPU for AI Plug-ins:** Cantai renders on the GPU through vkd3d-proton (per-app, pinned and checksum-verified) with Wine patch 0011 (dxcore reports Direct3D 12 / ML adapters only for a native d3d12). The strongest GPU is picked automatically (setting in Wine Tools > GPU for AI Plug-ins). The container gets NVIDIA access (`distrobox --nvidia`) on NVIDIA hosts; existing installs are offered a quick container conversion. Fresh 4-part SATB render: CPU 44-47 s, Intel Iris Xe 36-37 s, NVIDIA RTX 3080 Ti Laptop 20-24 s.
*   **Uninstall License Guard:** The uninstaller reads the Activation Manager's activation data and refuses to delete activated Steinberg licenses unless the user types an explicit override.
*   **Log Exporter:** `torquio -l` / "Export Logs" zips Torquio, Wine, Dorico and Steinberg logs plus a system summary into `~/Downloads`, with emails, the username, the computer name, sign-in tokens and license IDs removed.
*   **Update Torquio:** `torquio -u` / "Update Torquio" fetches the latest version, then refreshes launchers and prefix settings and offers a Wine engine rebuild or NVIDIA container conversion when needed.
*   **Status Dashboard:** New "GPU for AI Plug-ins" section.

**Build Environment Artifacts:**
*   **Custom Wine Source (`zhiyi/wine`):** Commit `883970826c62286c3da998072a5f49813d333a31`
*   **Torquio Wine Patches:** `0001`-`0003` (unchanged), `0004-dxgi-vblank-and-frame-latency-dcomp-presented-buffer`, `0005-dcomp-layered-popups-transparent-corners-no-black-flash`, `0006-ole32-revokedragdrop-other-process-windows`, `0007-dcomp-dwmapi-windows11-rounded-popup-corners`, `0008-winex11-hide-layered-windows-until-drawn`, `0009-dcomp-cross-process-targets-compose-on-change`, `0010-kernelbase-answer-wmic-uuid-query-without-a-process`, `0011-dxcore-report-d3d12-ml-adapters-for-native-d3d12`
*   **vkd3d-proton:** `3.0.1`
*   **WebView2 Runtime:** `156.0.4314.42` (fetched at install time)
*   **Winetricks Version:** `20240105`
*   **Wine-ICU MSI Version:** `72.1`

**Verified Application Versions:**
*   **Steinberg Download Assistant (SDA):** `1.40.1`
*   **Steinberg Activation Manager (SAM):** `1.10.0.1489`
*   **Steinberg Media Bay:** `1.3.80`
*   **Dorico:** `6.2.30.6245`
*   **NotePerformer (3rd Party):** `5.1.2`
*   **Cantai (3rd Party):** `3.1.1`

**Known Issues:**
*   SDA attempts to update MediaBay automatically and fails (Error 231: `preinstall.ps1: not trusted`); MediaBay stays at the version from the provided installer.
*   The Activation Manager asks you to sign in every time it opens (its License Engine discards the stored sign-in on start); licenses stay activated.
*   Cantai's editor shows white for a few seconds when first opened (WebView2 start-up); score edits made while Cantai's renderer is starting aren't rendered until the next edit; its renderer stays running for ~2 minutes after Dorico quits.
*   GPU rendering for Cantai is verified on Intel Iris Xe (Mesa) and NVIDIA (proprietary 615); other GPUs/drivers are untested. It can be turned off in Wine Tools > GPU for AI Plug-ins.
*   ntsync requires a host kernel 6.14+ with `CONFIG_NTSYNC`. On older kernels Wine falls back to the wineserver path.

---

## **Release v0.3.5-alpha (ntsync & DirectComposition Fixes)**
**Date:** 2026-10-19
**Status:** Alpha / Milestone

**Description:** Enabled kernel fast sync (ntsync) in the custom Wine build, bringing large-score UI operations in line with Windows performance. Bumped the `zhiyi/wine` target commit and added DirectComposition patches that resolve the blank-dropdown regression. Verified with a from-scratch install on a fresh Fedora Silverblue VM.

**Key Improvements:**
*   **Kernel Fast Sync (ntsync):** `build_wine.sh` injects `linux/ntsync.h` (vendored in `scripts/1-build/include/`, with fallback to host kernel headers) so Wine's `configure` no longer silently disables ntsync in the ubuntu:24.04 container. Also re-enables the wineserver in-process ntsync device handle. Reported in #5: Select All on a 23-page score dropped from 108 s to 6.2 s.
*   **ntsync Activation:** The installer prompts to load and persist the `ntsync` kernel module (requires sudo). Also available via `./torquio --enable-ntsync` and the interactive menu. The status dashboard reports whether ntsync is active, supported but dormant, or unavailable.
*   **DirectComposition Patches:** Added three patches on top of `zhiyi/wine`: composition swapchain (dcomp/dxgi), `IDCompositionVirtualSurface` + D2D device interop, and `ID2D1DeviceContext` draw surface support. Dropdowns no longer render blank white on re-open (#6).
*   **Wine Rebuild Flag:** Added `--rebuild-wine` to recompile the custom Wine engine inside the container.
*   **Prerequisite Docs:** Corrected the Fedora Atomic distrobox install command and clarified that traditional distros should install Distrobox/Podman from their package manager (#4).

**Build Environment Artifacts:**
*   **Custom Wine Source (`zhiyi/wine`):** Commit `883970826c62286c3da998072a5f49813d333a31`
*   **Torquio Wine Patches:** `0001-dcomp-dxgi-composition-swapchain`, `0002-dcomp-virtual-surface`, `0003-dcomp-d2d1-device-context-support`
*   **Winetricks Version:** `20240105`
*   **Wine-ICU MSI Version:** `72.1`

**Verified Application Versions:**
*   **Steinberg Download Assistant (SDA):** `1.40.1`
*   **Steinberg Activation Manager (SAM):** `1.10.0.1489`
*   **Steinberg Media Bay:** `1.4.10.19`
*   **Dorico:** `6.2.30.6245`
*   **NotePerformer (3rd Party):** `5.1.2`

**Known Issues:**
*   Dropdown content is not yet fully correct (#6). Dropdowns now render consistently on repeated opens, but work to fully resolve them continues on a follow-up branch.
*   ntsync requires a host kernel 6.14+ with `CONFIG_NTSYNC`. On older kernels Wine falls back to the wineserver path.
*   SDA attempts to update MediaBay automatically and fails due to `preinstall.ps1` block (Error 231).
*   3rd-party Cantai VST testing has not been successful. The initial work to patch DComp to fix the instrument window has been successfully completed (that window no longer crashes Dorico and is confirmed to work with Noteperformer), but attempting to launch that window with Cantai is not successful.

---

## **Release v0.3.0-alpha (CLI App & Compatibility Polish)**
**Date:** 2026-07-11
**Status:** Alpha / Milestone

**Description:** Consolidated the framework into the `torquio` CLI manager, supporting both interactive text menus and command-line flags. Implemented key compatibility remedies, automatic scaling overrides, custom debugging utilities, and native DBus URL handoffs.

**Key Improvements:**
*   **Torquio CLI Manager:** A single console app `torquio` mapping interactive dashboards, setup utilities, and CLI flags.
*   **Automatic Scaling & Auto-DPI:** Queries active host monitor specs on boot to automatically set target Wine DPI and adjust Wayland desktop compositor XWayland scaling.
*   **Modal Focus Loss Mitigation:** Injects X11 Driver keys to force focus acquisition, avoiding dialog keyboard lockups.
*   **Keyboard repeat rate tuning:** Fixes repeat delay lag inside the container.
*   **Custom Debugger Suppressor:** Compiles a native Windows helper `torquio-winedbg.exe` to suppress Wine console debug alerts and cleanly silence background daemon exit crashes. This allows us to send both app logs and Wine debug logs to the same log file.
*   **DBus browser integration:** Maps prefix HTTP/HTTPS protocol handlers directly to the host portal via `busctl`. This works around downstream effects of the debug suppression.
*   **CUPS Spooler Bridge:** Added native printing dependencies (`libcups2`) inside container packages.
*   **Folder Mapping:** Supports Zenity/KDialog interactive drive mappings.
*   **Key Command Backups:** Zip-based import/export system for key bindings.

**Build Environment Artifacts:**
*   **Custom Wine Source (`zhiyi/wine`):** Commit `ae88a705b5aa544cc60153d48c1ca8849f32ee14`
*   **Winetricks Version:** `20240105`
*   **Wine-ICU MSI Version:** `72.1`

**Verified Application Versions:**
*   **Steinberg Download Assistant (SDA):** `1.39.3`
*   **Steinberg Activation Manager (SAM):** `1.8.1.1383`
*   **Steinberg Media Bay:** `1.3.80.59`
*   **Dorico:** `6.2.30.6245`
*   **NotePerformer (3rd Party):** `5.1.2`

**Known Issues:**
*   SDA attempts to update MediaBay automatically and fails due to `preinstall.ps1` block (Error 231).
*   3rd-party Cantai VST testing is inconclusive. While it installs and the playback template loads and seems to load the correct amount of instances, license activation requires opening the VST window, which currently crashes Dorico in this build (and all previous builds).

---

## **Release v0.2.0-alpha (Automated Installer)**
**Date:** 2026-05-19
**Status:** Alpha / Milestone

**Description:** Major UX overhaul featuring the `install.sh` master orchestrator. This release automates the entire lifecycle from container creation to host integration, significantly reducing manual intervention.

**Key Improvements:**
*   **Master Orchestrator:** Single entry point (`install.sh`) for the entire installation process.
*   **Auto-Accept Flag:** Added `-y` / `--yes` support to bypass prompts and the SDA launch pause.
*   **Process Polling:** Implemented a polling loop to wait for detached SDA processes to terminate before finalizing.
*   **Double-Pass Integration:** Automated a second icon extraction pass to capture Dorico and SAM after their installation via SDA.

**Build Environment Artifacts:**
*   **Custom Wine Source (`zhiyi/wine`):** Commit `ae88a705b5aa544cc60153d48c1ca8849f32ee14`
*   **Winetricks Version:** `20240105`
*   **Wine-ICU MSI Version:** `72.1`

**Verified Application Versions:**
*   **Steinberg Download Assistant (SDA):** `1.39.3`
*   **Steinberg Media Bay:** `1.3.70`
*   **Dorico:** `6.2.20.6183`
*   **NotePerformer (3rd Party):** `5.1.2`

**Known Issues:**
*   SDA attempts to update MediaBay automatically and fails.
*   3rd-party Cantai VST testing is inconclusive. While it installs and the playback template loads and seems to load the correct amount of instances, license activation requires opening the VST window, which currently crashes Dorico in this build (and all previous builds).
*   Visual glitches (transparent text) in SDA.
*   `VSTAudioEngine6.exe` crashes cleanly upon closing Dorico.
*   Wine DPI scaling may need to be manually set on any given display, e.g. high-resolution (4K) displays.

---

## **Release v0.1.2-alpha**
**Date:** 2026-05-09
**Status:** Alpha / Work-in-Progress

**Description:** Validated minor update of Dorico (6.2.20.6183) installed via the existing SDA installation. Includes partial testing of 3rd-party VST (Cantai).

**Build Environment Artifacts:**
*   **Custom Wine Source (`zhiyi/wine`):** Commit `ae88a705b5aa544cc60153d48c1ca8849f32ee14`
*   **Winetricks Version:** `20240105`
*   **Wine-ICU MSI Version:** `72.1`

**Verified Application Versions:**
*   **Steinberg Download Assistant (SDA):** `1.39.3`
*   **Steinberg Activation Manager (SAM):** `1.8.1.1383`
*   **Steinberg Media Bay:** `1.3.60`
*   **Dorico:** `6.2.20.6183` (AudioEngine version `6.1.0.13`)
*   **NotePerformer (3rd Party):** `5.1.2`
*   **Cantai (3rd Party):** `2.2.0` PARTIAL (see note below)

**Known Issues (in this environment):**
*   **New:** SDA attempts to update MediaBay automatically and fails.
*   **New:** 3rd-party Cantai VST testing is inconclusive. While it installs and the playback template loads and seems to load the correct amount of instances, license activation requires opening the VST window, which currently crashes Dorico in this build (and all previous builds).
*   Visual glitches (transparent text) in SDA.
*   `VSTAudioEngine6.exe` crashes cleanly upon closing Dorico.
*   Wine DPI scaling may need to be manually set on any given display, e.g. high-resolution (4K) displays.

---

## **Release v0.1.1-alpha**
**Date:** 2026-04-01
**Status:** Alpha / Work-in-Progress

**Description:** Validated minor update of Dorico (6.2.10.6140) installed via the existing SDA installation.

**Build Environment Artifacts:**
*   **Custom Wine Source (`zhiyi/wine`):** Commit `ae88a705b5aa544cc60153d48c1ca8849f32ee14`
*   **Winetricks Version:** `20240105`
*   **Wine-ICU MSI Version:** `72.1`

**Verified Application Versions:**
*   **Steinberg Download Assistant (SDA):** `1.39.3`
*   **Steinberg Activation Manager (SAM):** `1.8.1.1383`
*   **Steinberg Media Bay:** `1.3.60`
*   **Dorico:** `6.2.10.6140`
*   **NotePerformer (3rd Party):** `5.1.2`

**Known Issues (in this environment):**
*   Visual glitches (transparent text) in SDA.
*   `VSTAudioEngine6.exe` crashes cleanly upon closing Dorico.
*   Wine DPI scaling may need to be manually set on any given display, e.g. high-resolution (4K) displays.

---

## **Release v0.1-alpha**
**Date:** 2026-03-22
**Status:** Alpha / Work-in-Progress

**Description:** The initial proof-of-concept environment capable of running Dorico 6 with NotePerformer via Distrobox and a custom Wine build.

**Build Environment Artifacts:**
*   **Custom Wine Source (`zhiyi/wine`):** Commit `ae88a705b5aa544cc60153d48c1ca8849f32ee14`
*   **Winetricks Version:** `20240105`
*   **Wine-ICU MSI Version:** `72.1`

**Verified Application Versions:**
*   **Steinberg Download Assistant (SDA):** `1.39.3`
*   **Steinberg Activation Manager (SAM):** `1.8.1.1383`
*   **Steinberg Media Bay:** `1.3.60`
*   **Dorico:** `6.2.0.6088` (AudioEngine version `6.1.0.13`)
*   **NotePerformer (3rd Party):** `5.1.2`

**Known Issues (in this environment):**
*   Visual glitches (transparent text) in SDA.
*   `VSTAudioEngine6.exe` crashes cleanly upon closing Dorico.
*   Wine DPI scaling may need to be manually set on any given display, e.g. high-resolution (4K) displays.