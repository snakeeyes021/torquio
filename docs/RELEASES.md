# Release Manifest & Version History

This document tracks known-good, tested "snapshots" of the entire system. It serves as a single source of truth for reproducibility, ensuring we know exactly which build environment artifacts and software versions successfully worked together at a given point in time.

---

## **Release v0.7.0-alpha (The Torquio App; MediaBay Updates Without Errors)** *(draft, not released yet)*
**Date:** TBD
**Status:** Alpha / Milestone

**Description:** Torquio's app: everything the `torquio` menu does, in a GNOME window, for people who'd rather not use a terminal (built from this repository, for Flathub as `tech.redfoxlabs.Torquio`). The command line stays, and both use the same core. MediaBay updates from the Download Assistant now install with no error. The Wine engine is unchanged from v0.6.5 (`build-3f3a8cb19fee`), so there's nothing large to download.

**Key Improvements:**
*   **The App:** a setup assistant (it checks what's needed, finds your installers, asks a few questions and installs Torquio, downloading Torquio itself first if the computer has none), then Overview (start Dorico, the Activation Manager and the Download Assistant; the engine, container, kernel fast sync and playback plug-ins), Display & Scaling, Folders, Key Commands, AI Plug-ins and Maintenance (Wine's tools, repairs, engine updates and rebuilds, logs for bug reports, uninstalling, with the same license and project checks as the terminal). It drives the computer's own copy of Torquio (`torquio api`, JSON), offers to update one that's too old for it, finishes a task even if its window is closed, and runs one task at a time.
*   **MediaBay Updates Without Errors:** Steinberg's Install Assistant runs a step of each MediaBay update through Windows PowerShell's .NET library, which Wine doesn't have, so it skipped MediaBay. Torquio now builds its own small stand-in for that library in the prefix (with the prefix's .NET compiler; our own code, nothing of Microsoft's or Steinberg's). It does that step's job: it stops MediaBay's server, or cancels the update cleanly while Dorico uses MediaBay (Torquio then installs it after the Download Assistant closes, as before). **Existing installs get the stand-in only through Update Torquio (`torquio -u`, or the app's Update) or Fix Icons & Refresh Launchers (`torquio -f`)**, which build it into the prefix; until then MediaBay updates behave as in v0.6.5.
*   **`torquio api`:** the interface the app uses (API 2): settings, display, folders, key commands, GPUs, prerequisites, updates, the uninstall checks, and long tasks as streamed JSON events.

**Build Environment Artifacts:** as v0.6.5-alpha (container image `ghcr.io/snakeeyes021/torquio-env:build-3f3a8cb19fee`). The app: GNOME 50 runtime.

---

## **Release v0.6.5-alpha (Fixes from the v0.6.0 Testing: Dialogs, Sign-In, MediaBay)**
**Date:** 2026-11-03
**Status:** Alpha / Milestone

**Description:** Fixes for what testing v0.6.0 found, released ahead of the GUI (v0.7.0) because one of them stops Dorico from closing with unsaved work. The Activation Manager now stays signed in, Dorico and HALion Sonic no longer abort on exit, MediaBay updates get installed, and the installer and launchers handle more situations gracefully. Torquio's Wine engine gains two patches, so Update Torquio offers the new engine (a download of about 1.5 GB; Dorico, your settings and your licenses are kept). Verified in a Fedora Workstation 44 VM (GNOME, no zenity) and on RedFoxOS, a Bazzite-based Fedora Atomic image (Intel Iris Xe + NVIDIA RTX 3080 Ti Laptop): signed in to the Activation Manager across restarts of it and of Dorico, MediaBay at 1.4.10 with no error from the Download Assistant, Cantai rendering on the GPU, HALion Sonic's editor opened and Dorico quit cleanly.

**Key Improvements:**
*   **No Restarts Without Asking:** On desktops without zenity or kdialog (stock Fedora Workstation, for one), the launchers took every question as a yes: with Dorico open and the display scale changed, starting a Steinberg program again restarted Wine and closed Dorico, losing unsaved work. Questions and warnings now use a GTK dialog where zenity and kdialog are missing (PyGObject, which GNOME desktops have), and where nobody can be asked Wine isn't restarted; a notification says the change applies on the next start. The "could not be located" errors are shown at last (the container has no dialog tools), and the clock warning appears before the Activation Manager starts instead of behind its window.
*   **The Activation Manager Stays Signed In:** Wine didn't store a credential's attributes, and Steinberg's License Engine keeps its sign-in with one, so it took its own sign-in for an outdated one and signed you out on every start. Wine patch 0013, vstenv's advapi32 patch (credited below), stores and returns them.
*   **Clean Exits:** The same patch provides `CloseThreadWaitChainSession`, which Dorico's processes and HALion Sonic call on exit; without it Wine aborted the process and started its debugger.
*   **MediaBay Updates:** Steinberg's Install Assistant checks the signature of a script in each MediaBay update, and Wine couldn't check PowerShell scripts' signatures (error 231). Wine patch 0012, Torquio's own PowerShell signature provider, verifies them as Windows does (changed or unsigned scripts are still refused). The Install Assistant still can't run the script under Wine, so Torquio installs the update the Download Assistant downloaded after it closes, and after Update Torquio: MediaBay stays current, and the Download Assistant reports a problem at most once per MediaBay update instead of on every start. Running the script natively is planned for v0.7.0.
*   **NotePerformer & Cantai Template:** With both plug-ins installed, Dorico gets a "NotePerformer & Cantai" playback template: Cantai for the voices, NotePerformer for everything else.
*   **Installer:** `torquio -i -y` keeps your settings instead of resetting them; missing installers are reported before anything is changed; and an open Steinberg program is closed (after asking) instead of stopping the reinstall at its installer's "still running" warning.
*   **Leftovers:** The uninstaller and Fix Icons also remove the icons Wine's menu builder made for Steinberg's programs, and Fix Icons removes the `.vstsound` file types of Wine's old launchers.
*   **Smaller Fixes:** "Choose a GPU" says when there's no GPU instead of asking `GPU (1-0)`; after `torquio --rebuild-wine` the dashboard says the engine was compiled locally (and replacing the container keeps that engine).
*   **Groundwork for the GUI:** `torquio api version` and `torquio api status` answer in JSON, for the app coming in v0.7.0.
*   **Thanks:** to [vstenv](https://github.com/dguedry/vstenv) for the credential-attributes patch (0013, LGPL-2.1-or-later, like Wine) and the cause of the Activation Manager's sign-outs, and to [steinberg_fix](https://github.com/chiarfe/steinberg_fix), which confirmed what MediaBay's error 231 is. `docs/REFERENCE_PROJECTS.md` compares the three projects.

**Build Environment Artifacts:**
*   **Custom Wine Source (`zhiyi/wine`):** Commit `883970826c62286c3da998072a5f49813d333a31` (`wine-11.5-191-g883970826c6`)
*   **Torquio Wine Patches:** `0001-dcomp-dxgi-composition-swapchain`, `0002-dcomp-virtual-surface`, `0003-dcomp-d2d1-device-context-support`, `0004-dxgi-vblank-and-frame-latency-dcomp-presented-buffer`, `0005-dcomp-layered-popups-transparent-corners-no-black-flash`, `0006-ole32-revokedragdrop-other-process-windows`, `0007-dcomp-dwmapi-windows11-rounded-popup-corners`, `0008-winex11-hide-layered-windows-until-drawn`, `0009-dcomp-cross-process-targets-compose-on-change`, `0010-kernelbase-answer-wmic-uuid-query-without-a-process`, `0011-dxcore-report-d3d12-ml-adapters-for-native-d3d12`, `0012-wintrust-verify-powershell-script-signatures`, `0013-advapi32-credential-attributes`
*   **Container Image:** `ghcr.io/snakeeyes021/torquio-env:build-3f3a8cb19fee`
*   **Container:** `Ubuntu 24.04.5 LTS`, Mesa `25.2.8-0ubuntu0.24.04.4`
*   **vkd3d-proton:** `3.0.1`
*   **WebView2 Runtime:** `156.0.4314.42` (fetched at install time)
*   **Winetricks Version:** `20240105`
*   **Wine-ICU MSI Version:** `72.1`

**Verified Application Versions:**
*   **Steinberg Download Assistant:** `1.40.1`
*   **Steinberg Activation Manager:** `1.10.0.1489`
*   **Steinberg MediaBay:** `1.4.10.19`
*   **Steinberg Dorico 6:** `6.2.30.6245`
*   **Cantai (3rd Party):** `4.0.0.926`
*   **NotePerformer (3rd Party):** `5.1.2`

**Known Issues:**
*   The Download Assistant can still report a failed MediaBay update once per MediaBay update, before Torquio installs it (planned for v0.7.0).
*   Cantai's editor shows white for a few seconds when first opened (WebView2 start-up); its renderer stays running for ~2 minutes after Dorico quits.
*   GPU rendering for Cantai is verified on Intel Iris Xe (Mesa) and NVIDIA (proprietary 615); other GPUs/drivers are untested. It can be turned off in Wine Tools > GPU for AI Plug-ins.
*   A new container's first start takes about a minute longer (distrobox installs its base packages).
*   32-bit programs that crash use Wine's default crash handling rather than Torquio's (only the 64-bit debugger setting points at it); Dorico and its audio engine are 64-bit.
*   ntsync requires a host kernel 6.14+ with `CONFIG_NTSYNC`. On older kernels Wine falls back to the wineserver path.

---

## **Release v0.6.0-alpha (Torquio in Python)**
**Date:** 2026-11-02
**Status:** Alpha / Milestone

**Description:** Torquio's host-side Bash is rewritten in standard-library Python (3.9 or newer, no other dependencies), organised as a core library with a thin command-line interface on top, which the planned GUI will reuse. Commands, flags, menus, wording and files stay the same, and existing installs update with Update Torquio as before. Testing the port turned up a few older problems, fixed here: a second Dorico in "Open With", fonts failing to install where `aria2c` is present, and KDE Plasma 6's scale not being read. Verified in a Fedora Workstation 44 VM (GNOME): a real update of a working v0.5.0 install (from the menu and with `torquio -u`), the uninstaller, and a from-scratch install (the wizard and `torquio -i -y`); the dashboard in a Fedora 44 KDE Plasma VM; and on RedFoxOS, a Bazzite-based Fedora Atomic image (Intel Iris Xe + NVIDIA RTX 3080 Ti Laptop): Fix Icons & Refresh Launchers, the GPU chooser, re-creating the container with Cantai staying activated, Cantai playback, and opening `.dorico` files from the file manager.

**Key Improvements:**
*   **Torquio in Python:** `torquio` is now a small Python entry point over the `lib/torquio` package (menus, installer, updater, uninstaller, engine and container management, Wine Tools, launchers). The launchers in `~/.local/bin` are short Python files that run your Torquio folder's code, so keep the folder where you installed it (as `~/.local/bin/torquio` always needed); `torquio_graphics.py` is no longer copied there. Unit tests, a parity harness that compared each stage with the Bash version, and a CI workflow come with it. The plan and the list of deliberate differences are in `docs/REFACTOR.md`.
*   **Python Version Check:** On a Python older than 3.9 (e.g. openSUSE Leap 15 and RHEL 8, whose default `python3` is 3.6), `torquio` says which version it needs.
*   **Launchers in Automated Mode:** Dorico, the Activation Manager and the Download Assistant now start on desktops the scaling automation doesn't cover, on COSMIC before its XWayland setting exists, and on KDE when `kreadconfig` fails; the Bash launchers stopped silently there.
*   **One Dorico in "Open With":** Wine's menu builder turned the prefix's file types and protocols (`.dorico`, `.vstsound`, Steinberg sign-in links, `http`) into launchers and file types on the host, duplicating Torquio's. It was only disabled for processes started with Torquio's `WINEDLLOVERRIDES`, which some winetricks packages replace; it's now disabled in the prefix itself, and Update Torquio and Fix Icons & Refresh Launchers remove what it created.
*   **Reliable Font Install:** Winetricks prefers `aria2c` when it's installed, and SourceForge answers `aria2c` with 403, so `allfonts` failed on such systems; winetricks now downloads with `curl`.
*   **KDE Plasma 6 Scaling:** Newer `kscreen-doctor` colours its output even into a pipe, which hid the scale and monitor from Torquio, and reports the scaled size as Geometry; Torquio now reads the scale and the monitor's real resolution.
*   **Smaller Fixes:** Log export reads the settings file Torquio actually writes; Configure Graphics and the uninstaller's banners show their intended colours (and no stray `033[0m`); key command export always uses `$XDG_DOWNLOAD_DIR` or `~/Downloads`.

**Build Environment Artifacts:**
*   **Custom Wine Source (`zhiyi/wine`):** Commit `883970826c62286c3da998072a5f49813d333a31` (`wine-11.5-191-g883970826c6`)
*   **Torquio Wine Patches:** `0001-dcomp-dxgi-composition-swapchain`, `0002-dcomp-virtual-surface`, `0003-dcomp-d2d1-device-context-support`, `0004-dxgi-vblank-and-frame-latency-dcomp-presented-buffer`, `0005-dcomp-layered-popups-transparent-corners-no-black-flash`, `0006-ole32-revokedragdrop-other-process-windows`, `0007-dcomp-dwmapi-windows11-rounded-popup-corners`, `0008-winex11-hide-layered-windows-until-drawn`, `0009-dcomp-cross-process-targets-compose-on-change`, `0010-kernelbase-answer-wmic-uuid-query-without-a-process`, `0011-dxcore-report-d3d12-ml-adapters-for-native-d3d12`
*   **Container Image:** `ghcr.io/snakeeyes021/torquio-env:build-f568ffd9a7fc`
*   **Container:** `Ubuntu 24.04.5 LTS`, Mesa `25.2.8-0ubuntu0.24.04.4`
*   **vkd3d-proton:** `3.0.1`
*   **WebView2 Runtime:** `156.0.4314.42` (fetched at install time)
*   **Winetricks Version:** `20240105`
*   **Wine-ICU MSI Version:** `72.1`

**Verified Application Versions:**
*   **Steinberg Download Assistant:** `1.40.1`
*   **Steinberg Activation Manager:** `1.10.0.1489`
*   **Steinberg MediaBay:** `1.3.80.59`
*   **Steinberg Dorico 6:** `6.2.30.6245`
*   **Cantai (3rd Party):** `3.1.1`
*   **NotePerformer (3rd Party):** `5.1.2`

**Known Issues:**
*   Without `zenity` or `kdialog` (e.g. on a stock Fedora Workstation), the launchers' questions get no dialog and are answered yes (e.g. Wine restarts without asking after a display scale change), as in earlier versions.
*   The warning about an out-of-sync system clock opens behind the Activation Manager.
*   After `torquio --rebuild-wine`, the dashboard still says the engine is prebuilt.
*   SDA attempts to update MediaBay automatically and fails (Error 231: `preinstall.ps1: not trusted`); MediaBay stays at the version from the provided installer.
*   The Activation Manager asks you to sign in every time it opens (its License Engine discards the stored sign-in on start); licenses stay activated.
*   Cantai's editor shows white for a few seconds when first opened (WebView2 start-up); score edits made while Cantai's renderer is starting aren't rendered until the next edit; its renderer stays running for ~2 minutes after Dorico quits.
*   GPU rendering for Cantai is verified on Intel Iris Xe (Mesa) and NVIDIA (proprietary 615); other GPUs/drivers are untested. It can be turned off in Wine Tools > GPU for AI Plug-ins.
*   A new container's first start takes about a minute longer (distrobox installs its base packages).
*   32-bit programs that crash use Wine's default crash handling rather than Torquio's (only the 64-bit debugger setting points at it); Dorico and its audio engine are 64-bit.
*   ntsync requires a host kernel 6.14+ with `CONFIG_NTSYNC`. On older kernels Wine falls back to the wineserver path.

---

## **Release v0.5.0-alpha (Prebuilt Wine Engine, Version Manifest & Plug-in Icons)**
**Date:** 2026-10-24
**Status:** Alpha / Milestone

**Description:** Torquio's Wine engine is now built by GitHub Actions and published as a public container image, so installing and updating it is a download of about 1.5 GB instead of compiling Wine for 20-40 minutes. Engine updates swap the container and keep everything else: the Wine prefix, settings, licenses, NVIDIA access and the computer's identity (Cantai stays activated). Also: release notes' version sections are generated, plug-in windows get an icon, Wine updates no longer show `rundll32` errors, and the uninstaller checks for Cantai licenses and projects stored in the Wine prefix and leaves nothing behind. Verified on RedFoxOS, a Bazzite-based Fedora Atomic image (Intel Iris Xe + NVIDIA RTX 3080 Ti Laptop): a real update of an existing, locally compiled install to the published image and back (Cantai staying activated throughout), then an uninstall and a from-scratch install with the published image. From starting the installer to pressing play in Dorico took 36 minutes; Torquio's part, until it handed over to Steinberg's Download Assistant, took 17 of them.

**Key Improvements:**
*   **Prebuilt Wine Engine:** `scripts/1-build/Containerfile` builds the engine with the same `build_wine.sh` and ships it on Ubuntu 24.04 with only the runtime libraries (the build fails if anything Wine links to or loads at runtime is missing, 64- and 32-bit). GitHub Actions publishes it as `ghcr.io/snakeeyes021/torquio-env`, tagged by the hash of the Wine build files, so every copy of Torquio gets the engine built from exactly its own files; without a matching image (or with local changes to them) the installer compiles Wine as before. The image contains only free and open-source software, plus the complete patched Wine source it was built from.
*   **Engine Updates:** When an update changes the Wine engine, Torquio offers to download the new one and swaps the container (also from Wine Tools > Update / Rebuild Wine Engine), compiling only if it hasn't been published yet. This is offered whenever the engine is out of date, including on installs updated by hand with `git pull` or from before Update Torquio existed (their locally compiled engines have no build record). The dashboard shows where the engine came from and whether an update is available.
*   **Stable Computer Identity:** Wine derives the Windows system UUID (which Cantai's license is tied to) from a machine ID that each container used to generate for itself, so a re-created container looked like a new computer. New containers now get one derived from the host's (hashed), and container swaps keep the existing one. Older installs are offered a one-time switch to the derived ID after updating (or with `torquio --fix-identity`), once plug-ins tied to it such as Cantai are deactivated; the dashboard shows which kind of ID a container has.
*   **Crash Handler Ships with the Engine:** Torquio's crash handler (which logs crashes instead of showing Wine's crash windows) is now built with the Wine engine, so it's in every container, including ones from the prebuilt image; it used to be compiled into the container during prefix setup and was lost when the container was re-created.
*   **No `rundll32` Errors on Wine Updates:** Each Wine update re-registered .NET's `mscoree.dll`, which showed two "This application could not be started" errors with .NET 4.8 installed. A `rundll32`-only override skips that redundant step.
*   **Update Notice & Settings:** When you open Torquio it checks GitHub for a new version (at most once a day, silently when offline) and shows a notice at the top of the menu. A new Settings entry in the main menu turns the check off.
*   **Version Manifest:** `torquio --manifest` prints the "Build Environment Artifacts" and "Verified Application Versions" sections of these notes from the installed system, including the Wine engine's build record, and warns if the engine wasn't built from the current Wine build files. The log export includes it.
*   **Uninstall Checks:** The license guard now also lists an activated Cantai (with where to deactivate it) next to Steinberg's licenses, and the uninstaller lists Dorico projects stored inside the Wine prefix instead of showing a generic warning. It also removes the leftovers of Wine's menu builder (file-type launchers, Start menu entries, Desktop shortcuts, default-application entries) and keeps it out of the WebView2 setup, which had been creating them.
*   **Plug-in Window Icons:** Plug-in windows (NotePerformer's splash and instrument windows, Cantai's editor, ...) all belong to Dorico's audio engine and now show its icon instead of a generic one.

**Build Environment Artifacts:**
*   **Custom Wine Source (`zhiyi/wine`):** Commit `883970826c62286c3da998072a5f49813d333a31` (`wine-11.5-191-g883970826c6`)
*   **Torquio Wine Patches:** `0001-dcomp-dxgi-composition-swapchain`, `0002-dcomp-virtual-surface`, `0003-dcomp-d2d1-device-context-support`, `0004-dxgi-vblank-and-frame-latency-dcomp-presented-buffer`, `0005-dcomp-layered-popups-transparent-corners-no-black-flash`, `0006-ole32-revokedragdrop-other-process-windows`, `0007-dcomp-dwmapi-windows11-rounded-popup-corners`, `0008-winex11-hide-layered-windows-until-drawn`, `0009-dcomp-cross-process-targets-compose-on-change`, `0010-kernelbase-answer-wmic-uuid-query-without-a-process`, `0011-dxcore-report-d3d12-ml-adapters-for-native-d3d12`
*   **Container Image:** `ghcr.io/snakeeyes021/torquio-env:build-f568ffd9a7fc`
*   **Container:** `Ubuntu 24.04.5 LTS`, Mesa `25.2.8-0ubuntu0.24.04.4`
*   **vkd3d-proton:** `3.0.1`
*   **WebView2 Runtime:** `156.0.4314.42` (fetched at install time)
*   **Winetricks Version:** `20240105`
*   **Wine-ICU MSI Version:** `72.1`

**Verified Application Versions:**
*   **Steinberg Download Assistant:** `1.40.1`
*   **Steinberg Activation Manager:** `1.10.0.1489`
*   **Steinberg MediaBay:** `1.3.80.59`
*   **Steinberg Dorico 6:** `6.2.30.6245`
*   **Cantai (3rd Party):** `3.1.1`
*   **NotePerformer (3rd Party):** `5.1.2`

**Known Issues:**
*   SDA attempts to update MediaBay automatically and fails (Error 231: `preinstall.ps1: not trusted`); MediaBay stays at the version from the provided installer.
*   The Activation Manager asks you to sign in every time it opens (its License Engine discards the stored sign-in on start); licenses stay activated.
*   Cantai's editor shows white for a few seconds when first opened (WebView2 start-up); score edits made while Cantai's renderer is starting aren't rendered until the next edit; its renderer stays running for ~2 minutes after Dorico quits.
*   GPU rendering for Cantai is verified on Intel Iris Xe (Mesa) and NVIDIA (proprietary 615); other GPUs/drivers are untested. It can be turned off in Wine Tools > GPU for AI Plug-ins.
*   A new container's first start takes about a minute longer (distrobox installs its base packages).
*   32-bit programs that crash use Wine's default crash handling rather than Torquio's (only the 64-bit debugger setting points at it); Dorico and its audio engine are 64-bit.
*   ntsync requires a host kernel 6.14+ with `CONFIG_NTSYNC`. On older kernels Wine falls back to the wineserver path.

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