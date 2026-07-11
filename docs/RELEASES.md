# Release Manifest & Version History

This document tracks known-good, tested "snapshots" of the entire system. It serves as a single source of truth for reproducibility, ensuring we know exactly which build environment artifacts and software versions successfully worked together at a given point in time.

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
*   **Winetricks Version:** `20260125-next`
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
*   **Winetricks Version:** `20260125-next`
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
*   **Winetricks Version:** `20260125-next` (SHA256: `8f07319f32e96a7ad92f786bf8ee2e00d3c65f82debd33b6884e681b825ae67a`)
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
*   **Winetricks Version:** `20260125-next` (SHA256: `8f07319f32e96a7ad92f786bf8ee2e00d3c65f82debd33b6884e681b825ae67a`)
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
*   **Winetricks Version:** `20260125-next` (SHA256: `8f07319f32e96a7ad92f786bf8ee2e00d3c65f82debd33b6884e681b825ae67a`)
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