# Valerio: Master Deployment Playbook & SOP

This document serves as the Standard Operating Procedure (SOP) for deploying the Steinberg environment. 

It is intentionally designed as a hybrid document:
1. **The SOP:** It defines the execution sequence, context, and expected state for each phase of the installation.
2. **The Manual Guide:** A step-by-step tutorial for users to build the environment right now by executing the modular scripts.
3. **The Automation Blueprint:** The exact logical skeleton that the future `install.sh` master wrapper will automate.

---

## ⚠️ A Note on Reproducibility & Versions

Steinberg software and Wine are both moving targets. To ensure a successful build, **it is highly recommended that you use the specific versions of software and commit hashes that have been validated together.**

Before starting, please consult **[docs/RELEASES.md](RELEASES.md)**. 

---

## Phase 1: Host Preparation (Manual)

This phase establishes the isolated environment. The future master installer will likely handle this, but currently, it must be done manually on the host.

**Execution Context:** Host OS
**Prerequisites:** `distrobox` and `docker`/`podman` installed.

1. **Create the Environment:**
   ```bash
   distrobox create -i ubuntu:24.04 -n valerio-env --yes
   ```
2. **Enter the Container:**
   *(All Phase 2, 3, and 4 scripts must be executed inside this container).*
   ```bash
   distrobox enter valerio-env
   ```

---

## Phase 2: Engine Compilation

**Module:** `scripts/1-build/build_wine.sh`
**Execution Context:** Inside the container.
**What it does:** 
* Installs native dependencies (including the critical `libicu-dev`).
* Clones the validated custom Wine source (`zhiyi/wine`).
* Compiles the 32-bit and 64-bit engine.
* Installs it locally to `/opt/wine-custom`.

**Execution:**
```bash
# Note: Ensure the script is targeting the commit hash verified in RELEASES.md
./scripts/1-build/build_wine.sh
```

---

## Phase 3: Prefix Initialization & Core Dependencies

**Module:** `scripts/2-install/setup_prefix.sh`
**Execution Context:** Inside the container.
**Prerequisites:** The Wine engine must be compiled and present in `/opt/wine-custom`.
**What it does:**
* Creates the Windows 10 prefix at `~/.local/share/valerio/prefix`.
* Installs core dependencies via Winetricks (`d3dx9`, `dotnet48`, etc.).
* **Automated:** Downloads and installs `wine-icu-72.1` (required for Dorico).
* **Automated:** Extracts MediaBay and robustly cleans up blocked files (e.g., `preinstall.ps1`).

**Execution:**
```bash
# Ensure you have dropped MediaBay_Installer_win64.zip into the installers/ folder or ~/Downloads
./scripts/2-install/setup_prefix.sh
```

---

## Phase 4: Software Component Installation

**Execution Context:** Host OS (outside the container).
**Prerequisites:** The prefix must be initialized. Installers must be downloaded by the user and placed in `~/Downloads` or the `installers/` directory within the repository.

**1. Install MediaBay**
*   **Module:** `scripts/2-install/setup_prefix.sh` (Handling extraction for now)
*   **Manual Step:** Run the installer inside the container:
    ```bash
    cd "$HOME/.local/share/valerio/MediaBay_extracted" && cd MediaBay* && wine Setup.exe
    ```

**2. Install Steinberg Download Assistant (SDA)**
*   **Module:** `scripts/2-install/install_sda.sh`
*   **Execution:** `./scripts/2-install/install_sda.sh`
*   **Manual Fallback:** Run `wine Steinberg_Download_Assistant_...exe`.

**3. Install NotePerformer (Optional)**
*   **Module:** `scripts/2-install/install_noteperformer.sh`
*   **Execution:** `./scripts/2-install/install_noteperformer.sh`

**4. Install Cantai (Optional / Not-yet-working)**
*   **Module:** `scripts/2-install/install_cantai.sh`
*   **Execution:** `./scripts/2-install/install_cantai.sh`

---

## Phase 5: Host Integration

**Execution Context:** Host OS (Outside the container).
**Prerequisites:** Containerized setup is complete.
**What it does:** Maps the `.desktop` handlers to the host so browser login links correctly pipe back into the container.

**Execution:**
```bash
exit # Leave the container
mkdir -p ~/.local/bin
cp scripts/3-runtime_handlers/*.sh ~/.local/bin/
chmod +x ~/.local/bin/*.sh
cp desktop_stubs/*.desktop ~/.local/share/applications/
update-desktop-database ~/.local/share/applications/
```