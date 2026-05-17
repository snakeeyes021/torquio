# Valerio 
A unified installation framework for Dorico on Linux

## The Mission
This project aims to simplify the process of installing Steinberg's Dorico on Linux via WINE. Steinberg software has historically been difficult to run on Linux due in large part to installer complexity, account logins/license validation, and web-to-app token handoffs. Typically, if a user could get past these pain points, the software itself would run decently. 

To that end, our goal is to provide a **reproducible, automated, and user-friendly** deployment system.

---

## Prerequisites

Before running the installer, ensure your host system has the following installed:

1.  **Distrobox** (available in most standard repos) 
    - Alternatively **Distroshelf** (a graphical frontend for managing Distrobox containers, available via Flathub)
2.  **Docker** or **Podman**
    - If you don't know which one to get, go with Podman. It's in the major repos and is therefore easier to install, and for most people they're functionally identical (the only people for whom the differences are material are people who already know which one they need).

## Step 1: Download Installers

You must provide your own Steinberg installers. 

Download the following files from the Steinberg download pages for [Steinberg Download Assistant](https://o.steinberg.net/index.php?id=steinberg_download_assistant&L=1) and [Steinberg MediaBay](https://o.steinberg.net/index.php?id=15368&L=1) to your `~/Downloads` folder:

*   `Steinberg_Download_Assistant_*_Installer_win.exe` (Mandatory)
*   `MediaBay_Installer_win64.zip` (Mandatory)
*   `NotePerformer-Installer-*.exe` (3rd-party, Optional)

*Note: You do not need to download the Dorico installer itself. The Download Assistant will handle that once the environment is built.*

## Step 2: Install Valerio

Open your terminal and run the following commands to clone the repository and start the automated build process:

```bash
git clone https://github.com/snakeeyes021/valerio.git
cd valerio
./install.sh
```

*(You can append `-y` to `./install.sh` to bypass the installation manifest confirmation prompt).*

### What happens next?
The script will take a good while to run. It will:
1. Generate an isolated Ubuntu container.
2. Compile a custom version of Wine (with specific stubs required by Dorico).
3. Initialize a Windows 10 prefix and install core dependencies.
4. Pop up the Windows installers for MediaBay, the Download Assistant, and NotePerformer (if provided).
5. Map the Steinberg desktop shortcuts and web-login handlers to your native Linux application menu. 
    - Note: this part is still a work-in-progress. You may see multiple icons/app shortcuts be generated in your app drawer/menu. You'll generally want to always select the uglier ones without icons (the SDA and SAM have "handler" in the name as well). 

Once complete, the Steinberg Download Assistant will launch automatically so you can sign in and download Dorico! We recommend using the "Install All" button for now, as the Steinberg Download Assistant is mostly illegible under the current build.

---

## Uninstallation / Clean Start

If you ever need to completely wipe the Valerio environment (including the container, Wine prefix, and all installed software) to start fresh, simply run:

```bash
./scripts/cleanup.sh
```

---

## For Developers & Contributors

If you are looking to understand how this system works under the hood, contribute to the scripts, or read the historical design decisions, please refer to the `docs/` directory:

*   **[Architecture & Blueprint](docs/ARCHITECTURE.md):** The core technical design (Containers, Custom Wine, URI Handoffs).
*   **[Release Manifests](docs/RELEASES.md):** The verifiable combinations of Wine versions and Steinberg app versions.
*   **[Project Backlog](docs/BACKLOG.md):** Current tasks and active sprint items.
*   **[Manual Playbook](docs/PLAYBOOK.md):** The step-by-step procedure the automated scripts are based on.
*   **[AI Agent Guide](docs/AGENTS.md):** Rules and constraints for LLMs assisting with this repository.

### Repository Structure
```text
valerio/
├── README.md                 
├── desktop_stubs/            # URI handlers and .desktop templates for the host
├── docs/                     # Architectural, task, and release documentation
└── scripts/
    ├── common.sh             # Shared environment variables and paths
    ├── 1-build/              # Compiles the custom Wine engine
    ├── 2-install/            # Bootstraps the prefix and installs software
    └── 3-runtime_handlers/   # Wrappers to launch the apps and handle web-logins
```
