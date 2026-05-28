# Torquio
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

## Step 2: Install & Build
Open your terminal and run the following commands to clone the repository and start the automated build process:

```bash
git clone https://github.com/snakeeyes021/torquio.git
cd torquio
./scripts/install.sh
```

*(You can append `-y` to `install.sh` to bypass the installer manifest confirmation prompt and scale prompts for a completely silent, automated installation).*

### What happens next?
The build pipeline automatically handles all the heavy lifting:
1. Configures an isolated Ubuntu container.
2. Compiles a custom version of Wine (with specific stubs required by Dorico).
3. Initializes a Windows prefix, applies ClearType font configurations, and installs core dependencies.
4. Installs MediaBay, the Download Assistant, and NotePerformer (if provided).
5. Registers all application desktop shortcuts and web-login handlers to your native Linux application menu.
6. Installs the globally accessible `torquio` console utility to manage your environment easily.

After installation, the Steinberg Download Assistant will launch automatically. Once the it does, simply sign in and download Dorico as you normally would! When finished, close the Download Assistant, run the Activation Manager to activate your license, and you are ready to start notating!

---

## The Torquio Console Manager

Torquio provides a unified, friendly console utility to manage your environment. You can run it globally from your terminal at any time simply by typing:

```bash
torquio
```

### Premium QOL Features

*   **Console Dashboard**: Check the active status of your container dependencies, configuration preferences, and system details in a clean, colorized terminal screen.
*   **High-DPI Scaling Controls**: Set Torquio to automatically manage High-DPI display scaling so that Dorico renders properly given your monitor specs and settings.
*   **Problem Fixes**: Solves several annoying quirks of running Dorico on Linux, for instance, keyboard longpresses sending too many repeated key events, breaking scrubber functionality. 
*   **Startup Time Validation**: Produces warnings if attempting to run Steinberg Activation Manager with an incorrect time on the system clock, which can cause really tricky-to-diagnose Steinberg licensing activation errors.
*   **Dorico Shortcut Backups**: Easily back up or restore your custom keyboard shortcuts for convenient transport from/to other machines.
*   **One-Click Maintenance**: Fast shortcuts to run Wine configuration, edit the registry, open a graphical file manager inside the prefix, soft-reboot the environment, or shut down the server when needed.

---

## Uninstallation / Clean Start

If you ever need to completely wipe the Torquio environment (including the container, Wine prefix, configuration profiles, desktop integrations, and cache) to start fresh, simply run:

```bash
torquio --uninstall
```

*(Alternatively, run the cleanup script directly: `./scripts/cleanup.sh`)*

---

## For Developers & Contributors

If you are looking to understand how this system works under the hood, contribute to the scripts, or read the historical design decisions, please refer to the `docs/` directory:

*   **[Architecture & Blueprint](docs/ARCHITECTURE.md):** The core technical design (Containers, Custom Wine, URI Handoffs).
*   **[Contributing Guide](CONTRIBUTING.md):** Our standard Git workflow, development guidelines, and how to safely test your changes.
*   **[Release Manifests](docs/RELEASES.md):** The verifiable combinations of Wine versions and Steinberg app versions.
*   **[Project Backlog](docs/BACKLOG.md):** Current tasks and active sprint items.
*   **[AI Agent Guide](docs/AGENTS.md):** Rules and constraints for LLMs assisting with this repository.

### Repository Structure
```text
torquio/
├── README.md                 # This file
├── CONTRIBUTING.md           # Guidelines for contributing and testing
├── LICENSE                   # GNU General Public License v3.0
├── torquio                   # The main console orchestrator script
├── desktop_stubs/            # URI handlers, .desktop templates, and MIME XMLs
├── docs/                     # Architectural, task, and release documentation
└── scripts/
    ├── install.sh            # The main one-click installer script
    ├── cleanup.sh            # The environment uninstaller/wipe script
    ├── common.sh             # Shared environment variables and paths
    ├── 1-build/              # Compiles the custom Wine engine
    ├── 2-install/            # Bootstraps the prefix and installs software
    └── 3-runtime_handlers/   # Wrappers to launch the apps and handle web-logins
```

## Alpha Status

> [!WARNING]
> **Torquio is currently in an ALPHA state.** It is experimental software under active development. Standard features may change, break, or be removed without prior notice.
>
> **Use Torquio entirely at your own risk.** It is highly recommended to perform backups of any critical system configurations, files, or Steinberg project data before initializing or running this utility and especially if uninstalling/removing it.

## Legal & Disclaimer

Torquio is an independent, community-driven open-source project. It is not affiliated, associated, authorized, endorsed by, or in any way officially connected with **Steinberg Media Technologies GmbH**, **Yamaha Corporation**, or any of their subsidiaries or affiliates.

All product names, logos, copyrights, patents, and trademarks™ or registered® trademarks are the property of their respective owners. Their use in this project is for identification and interoperability purposes only and does not imply any association or endorsement.

Torquio does not distribute any proprietary Steinberg assets, binaries, or code. Users must provide their own legally obtained software to use this tool.
