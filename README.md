# Torquio
A unified installation framework for Dorico on Linux

## The Mission
This project aims to simplify the process of installing Steinberg's Dorico on Linux via WINE. Steinberg software has historically been difficult to run on Linux due in large part to installer complexity, account logins/license validation, including web-to-app token handoffs, and the like. Typically, if a user could get past these pain points, the software itself would run decently. 

To that end, our goal is to provide a **reproducible, automated, and user-friendly** deployment system.

---

## Prerequisites

Before running the installer, ensure your host system has the following installed:

1.  **Distrobox** (available in most standard repos) 
    - Optional addition: **Distroshelf** (a graphical frontend for managing Distrobox containers, available via Flathub)
2.  **Docker** or **Podman**
    - If you don't know which one to get, go with Podman. It's in the major repos and is therefore easier to install, and for most people they're functionally identical (the only people for whom the differences are material are people who already know which one they need).  

On many immutable distros, the above are included by default, so you're good to go. That includes:

* **The Universal Blue family** (Bazzite, Bluefin, Aurora, and most, if not all, custom downstream images)
* **SteamOS** (yes, it runs on Steam Deck, though there's no good gamepad profile for it yet)
* **openSUSE Aeon / Kalpa**  

> [!TIP]
> On the upstream Fedora Atomic family (Silverblue, Kinoite, etc.), by default Podman is available, but Distrobox is not, in favor of Toolbox. To install Distrobox, we recommend the sudo-free install to your user's local binary folder:
>
>```
>curl https://raw.githubusercontent.com/89luca89/distrobox/main/install | sh -s -- -p ~/.local/bin/
>```
>
>as suggested here: [https://fedoramagazine.org/run-distrobox-on-fedora-linux/](https://fedoramagazine.org/run-distrobox-on-fedora-linux/). This is the "custom directory" install detailed on Distrobox's [installation page](https://github.com/89luca89/distrobox#installation).



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
./torquio
```

Then just follow the interactive prompts to go through the install wizard.

*(You can alternatively run `./torquio -i -y` to bypass the installer wizard and other prompts for a silent, automated installation).*

### What happens next?
The build pipeline automatically handles all the heavy lifting:
1. Configures an isolated Ubuntu container.
2. Compiles a custom version of WINE (with specific stubs required by Dorico).
3. Initializes a Windows prefix, applies ClearType font configurations, and installs core dependencies.
4. Installs MediaBay, the Download Assistant, and NotePerformer (if provided).
5. Registers all application desktop shortcuts and web-login handlers to your native Linux application menu.
6. Installs the globally accessible `torquio` console utility to manage your environment easily.

After installation, the Steinberg Download Assistant will launch automatically. Once the it does, simply sign in and download Dorico as you normally would! When finished, close the Download Assistant, run the Activation Manager to activate your license, and you are ready to start notating!

---

### Features & CLI Usage Guide

Torquio is more than just an installer. It includes a unified console orchestrator (`torquio`) to manage your Dorico environment. You can interact with it through a friendly terminal-based menu interface by running:

```bash
torquio
```

Alternatively, you can bypass the interactive menus and run operations directly using command-line flags. Below is an overview of the core features and how to use them.

### 1. Interactive Status Dashboard
Displays active paths, checks if the Distrobox container is running, shows current Wine DPI settings and Freetype interpreter settings, and validates system clock synchronization (vital for Steinberg licensing).  

**How to Use**:
  * **Interactive**: Option `3` (Status Dashboard) in the main menu.
  * **CLI Flag**: `torquio -s` or `torquio --status`

### 2. Automated Display Scaling
Wine runs on legacy X11 protocols via XWayland. In high-resolution (4K+) or fractionally scaled environments, this can cause some headaches when trying to get things dialed in visually. The automated display scaling feature automatically queries your active monitor specs and dynamically configures the Wine registry DPI and desktop compositor scaling policies (on GNOME, KDE Plasma, and COSMIC Wayland sessions).  

**How to Use**:
  * **Interactive**: Option `4` (Configure Graphics & Scaling) in the main menu.
  * **CLI Flag**: `torquio -g` or `torquio --graphics`
  * *Note: For deep architectural details, formulas, and manual setups on less popular Wayland distros, or X11, see the [Display Scaling & Graphics Strategy](docs/GRAPHICS.md) guide.*

### 3. Project Folder Mapping
Wine prefixes isolate virtual Windows drives (like `C:\`), making your native Linux directories (e.g. `~/Documents` or Cloud-synced folders) difficult to navigate to from within WINE's file chooser (and it is highly highly recommended to never save your projects inside the WINE prefix itself). The folder mapping option helpfully creates symlinks inside the Wine prefix, mapping your native host project directories or cloud-sync folders directly to convenient locations in the virtual drive.  

**How to Use**:
  * **Interactive**: Option `6` (Manage Folder Mappings) in the main menu.
  * **CLI Flag**: `torquio -d [path/on/host] [link/name/in/prefix]` (or run without arguments for interactive prompts).

### 4. Key Commands Backup & Restore
This tool exports your custom Dorico keyboard shortcuts (`keycommands_*.json`, etc.) from the prefix to a zip archive on the host, and allows you to import them back at any time. If you have a key commands json you'd like to import from a previous installation (Linux or Windows), simply place the json in your ~/Downloads folder and run this tool to import it. Going forward, use the exporter to grab your key commands for use in new installations.  

**How to Use**:
  * **Interactive**: Option `7` (Manage Dorico Key Commands) in the main menu.
  * **CLI Flags**:
    * **Export**: `torquio -x` or `torquio --export_key_commands`
    * **Import**: `torquio -m` or `torquio --import_key_commands`

### 5. Environment Maintenance & Debugging Utilities
Occasionally, Wine servers hang, applications lock up in the background, or you're feeling adventurous and want to try installing third-party plugins/VSTs (at the moment our advice is this usually won't work, unless the VST, like Noteperformer, requires zero out-of-the-box configuration, but hey, doesn't hurt to try!). Torquio provides a small set of helper tools to keep the environment running smoothly.  

**How to Use**:
  * **Interactive**: Option `8` (Wine Tools & Maintenance) from the main menu provides submenus for all tasks.
  * **CLI Flags**:
    * **Kill Wine**: `torquio -k` or `torquio --kill_wine` (Force-stops the Wine server and all lingering Steinberg processes; useful if the app hangs).
    * **Reboot Prefix**: `torquio -b` or `torquio --reboot` (Simulates a Windows system reboot in the prefix).
    * **Wine Configuration**: `torquio -w` or `torquio --winecfg` (Opens the standard `winecfg` graphical control panel for library overrides).
    * **Execute Installer**: `torquio -e [file.exe/msi]` or `torquio --execute [file.exe/msi]` (Executes custom Windows installers or tools inside the environment prefix).
    * **Fix Icons**: `torquio -f` or `torquio --fix-icons` (Refreshes desktop icons and launcher shortcuts on the host system). This can also be useful when following a ```git pull```; at the moment, this is how you'd update Torquio.

---

## Display Scaling & Performance

Because Dorico runs via WINE (which currently operates on legacy X11 protocols via XWayland), high-resolution monitors can cause scaling headaches on modern Wayland desktop environments. 

Torquio provides an **Auto Graphics Mode** that handles this automatically by managing the desktop's XWayland scaling protocol as well as the WINE prefix's DPI setting. Auto Graphics Mode is available on recent versions **GNOME**, **KDE Plasma**, and **Cosmic** (it may work on older versions, but we can't guarantee how far back said compatibility extends). 

If you use standard 1080p/1440p monitors without fractional scaling, the default manual settings are usually perfect. However, if you are running a 4K+ monitor, use fractional scaling, or use a laptop that you occasionally plug into larger external monitors, you may want to turn on auto graphics mode or consult our guide:

**[Display Scaling & Graphics Guide](docs/GRAPHICS.md)**

This document details the scaling formulas, a visual strategy guide flowchart, manual configuration instructions for other Wayland compositors (like Sway/Hyprland) or X11 desktop environments (like Linux Mint/Cinnamon), and global scaling cautions.

----

## Uninstallation / Clean Start

If you ever need to completely wipe the Torquio environment (including the container, WINE prefix, configuration profiles, desktop integrations, and cache) to start fresh, simply run:

```bash
torquio --uninstall
```

> [!NOTE]
> If you installed Dorico prior to our name change (from "Valerio" to "Torquio"), we recommend uninstalling and performing a clean re-install to get yourself onto the new system. This also gives you access to future updates and features as they are released. However, the normal uninstall option will not work. For this specific situation, we have a Valerio-specific cleanup script, which you can run with the following command (assuming you're in the root of the git repo):
>
>```bash
>./scripts/cleanup_valerio.sh
>```
>
> The script will still prompt you to confirm that you've deactivated your licenses or backed up any projects you may have been (unwisely) storing in the prefix. Once complete, you can proceed with a normal installation of the new Torquio system following the instructions above.


---

## For Developers & Contributors

If you are looking to understand how this system works under the hood, contribute to the scripts, or read the historical design decisions, please refer to the `docs/` directory:

*   **[Architecture & Blueprint](docs/ARCHITECTURE.md):** The core technical design (Containers, Custom WINE, URI Handoffs).
*   **[Display Scaling & Graphics Guide](docs/GRAPHICS.md):** The math formulas, Mermaid decision guide, and manual configurations.
*   **[Contributing Guide](CONTRIBUTING.md):** Our standard Git workflow, development guidelines, and how to safely test your changes.
*   **[Release Manifests](docs/RELEASES.md):** The verifiable combinations of WINE versions and Steinberg app versions.
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
    ├── 1-build/              # Compiles the custom WINE engine
    ├── 2-install/            # Bootstraps the prefix and installs software
    └── 3-runtime_handlers/   # Wrappers to launch the apps and handle web-logins
```

## Project Status: Alpha

Torquio is fully functional for its primary job, but should be considered early-stage software. 

When using it, keep the following architectural realities in mind:
* **Version Breaking Changes**: As the project is optimized, future updates/features could in some rare circumstances require a full removal and reinstall. It's not tremendously likely, but we can't definitively promise that it could never happen (it's occurred exactly once, because of the name change; we're hoping that's the only one going forward).
* **Missing Features**: Some quality of life features have yet to be implemented, and there's no guarantee we'll ever cross everything off our wishlist. Initial build/install can take longer than we'd like, certain things are less automatic than they should be, and any number of other inconveniences could pop up here and there. We hope we've cast a pretty wide net and made Torquio work for most people who need it, but if something is just absolutely broken or some quirk of the way we've done things makes its use impossible with your setup, do of course open an issue above.
* **The prefix is just files in a folder**: But that's where Dorico and your Steinberg licenses live. While Torquio includes safety checks and prompts to prevent accidents, understand that running `torquio --uninstall` completely wipes the prefix.
    * **Licenses:** Because Steinberg licenses are stored *inside* the prefix, wiping the environment without deactivating your license first will permanently prevent access to it (thus requiring you to deactivate the license on Steinberg's website; we don't know if there's some sort of limit or monitoring for fraud prevention on this type of deactivation, nor would we like to find out, so we try to avoid this at all costs and recommend you do the same). Always deactivate via the Steinberg Activation Manager before a clean reinstall.
    * **Project Files:** Save your `.dorico` project files to your local user directory, not inside the prefix. Torquio provides a convenient tool to map links to your native host folders directly onto specific prefix locations, providing convenient access to them via the WINE file picker dialogs. To that end, not an advertisement, but we really love Insync (coupled with your cloud service of choice), which, yes, is proprietary/paid software, but it gets the job done and does so reliably. 

## Legal & Disclaimer

Torquio is an independent, community-driven open-source project. It is not affiliated, associated, authorized, endorsed by, or in any way officially connected with **Steinberg Media Technologies GmbH**, **Yamaha Corporation**, or any of their subsidiaries or affiliates.

All product names, logos, copyrights, patents, and trademarks™ or registered® trademarks are the property of their respective owners. Their use in this project is for identification and interoperability purposes only and does not imply any association or endorsement.

Torquio does not distribute any proprietary Steinberg assets, binaries, or code. Users must provide their own legally obtained software to use this tool.
