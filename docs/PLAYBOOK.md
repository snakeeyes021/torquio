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

## ⚠️ WARNING: Hardcoded Paths (Temporary)

Currently, the scripts have hardcoded paths expecting the repository to be located at `~/dev/steinberg-on-linux`. Because the project is now called **Valerio**, cloning it would create a folder named `valerio`. 

**Until this is fixed, you MUST do one of the following before proceeding:**
1. Clone the repo directly into the expected folder:
   `git clone <repo-url> ~/dev/steinberg-on-linux`
2. OR, if already cloned as `valerio`, simply rename the directory
   `mv ~/dev/valerio ~/dev/steinberg-on-linux`
3. OR, if you prefer to keep the folder name as is, create a symlink:
   `ln -s ~/dev/valerio ~/dev/steinberg-on-linux`

---

## Phase 1: Host Preparation (Manual)

This phase establishes the isolated environment. The future master installer will likely handle this, but currently, it must be done manually on the host.

**Execution Context:** Host OS
**Prerequisites:** `distrobox` and `docker`/`podman` installed.

1. **Create the Environment:**
   ```bash
   distrobox create -i ubuntu:24.04 -n steinberg-env
   ```
2. **Enter the Container:**
   *(All Phase 2, 3, and 4 scripts must be executed inside this container).*
   ```bash
   distrobox enter steinberg-env
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
* Creates the Windows 10 prefix at `$HOME/dev/steinberg-on-linux/dorico-prefix`.
* Installs core dependencies via Winetricks (`d3dx9`, `dotnet48`, etc.).

**Execution:**
```bash
./scripts/2-install/setup_prefix.sh
```

**⚠️ Temporary Manual Step (See Backlog):** 
Until `setup_prefix.sh` is updated to automate this, you must manually install the Wine-ICU MSIs into the prefix. (Check `RELEASES.md` for the correct version).
```bash
wget https://dl.winehq.org/wine/wine-icu/72.1/wine-icu-72.1-x86.msi
wget https://dl.winehq.org/wine/wine-icu/72.1/wine-icu-72.1-x86_64.msi
wine msiexec /i wine-icu-72.1-x86.msi
wine msiexec /i wine-icu-72.1-x86_64.msi
```

---

## Phase 4: Software Component Installation

**Execution Context:** Inside the container.
**Prerequisites:** The prefix must be initialized. Installers must be downloaded by the user and placed in a discoverable location (e.g., `~/Downloads`).

**1. Install MediaBay**
*   **Module:** `scripts/2-install/install_mediabay.sh` *(TODO: Currently handled haphazardly inside `setup_prefix.sh`)*
*   **Manual Fallback:** Unzip the MediaBay installer, delete the broken `preinstall.ps1`, and run `wine Setup.exe`.

**2. Install Steinberg Download Assistant (SDA)**
*   **Module:** `scripts/2-install/install_sda.sh` *(TODO)*
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
cp ~/dev/steinberg-on-linux/scripts/3-runtime_handlers/*.sh ~/.local/bin/
chmod +x ~/.local/bin/*.sh
cp ~/dev/steinberg-on-linux/desktop_stubs/*.desktop ~/.local/share/applications/
update-desktop-database ~/.local/share/applications/
```