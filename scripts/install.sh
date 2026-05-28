#!/bin/bash
set -e

# Torquio Master Installer
# This script automates the entire installation process for Steinberg software on Linux.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$SCRIPT_DIR/scripts/common.sh"

AUTO_ACCEPT=false
if [[ "$1" == "-y" ]] || [[ "$1" == "--yes" ]]; then
    AUTO_ACCEPT=true
fi

wine="\033[38;5;125m"
gray="\033[38;5;244m"
green="\033[38;5;108m"
red="\033[38;5;167m"
yellow="\033[38;5;179m"
reset="\033[0m"

echo -e "${gray}===========================================${reset}"
echo -e "   ${wine}Torquio: Steinberg on Linux Installer${reset}   "
echo -e "${gray}===========================================${reset}"
echo ""

# 1. Prerequisite Checks
echo "Checking prerequisites..."
if ! command -v distrobox >/dev/null 2>&1; then
    echo -e "${red}Error: distrobox is not installed.${reset}"
    echo "Please install distrobox and either docker or podman."
    exit 1
fi

# Check for docker or podman
if ! command -v docker >/dev/null 2>&1 && ! command -v podman >/dev/null 2>&1; then
    echo -e "${red}Error: Neither docker nor podman was found.${reset}"
    echo "Please install one of them to use with distrobox."
    exit 1
fi

# 2. Scaling Setup Pre-Installation Prompts
echo -e "${wine}=== Display Scaling Setup ===${reset}"
if [ "$AUTO_ACCEPT" = true ]; then
    set_config_val "auto_scale_mutter" "false"
    set_config_val "auto_dpi_detect" "true"
    set_config_val "manual_dpi" "96"
    echo -e "Using default: auto_scale_mutter=${wine}false${reset}, auto_dpi_detect=${wine}true${reset}"
else
    echo "Torquio can automatically manage host display scaling and Wine DPI settings to"
    echo "ensure that Dorico and other applications render correctly on High-DPI screens."
    echo ""
    read -p "Would you like Torquio to automatically manage display scaling and DPI? [Y/n]: " manage_scaling
    if [[ ! "$manage_scaling" =~ ^[Nn]$ ]]; then
        set_config_val "auto_scale_mutter" "true"
        set_config_val "auto_dpi_detect" "true"
        set_config_val "manual_dpi" "96"
        echo -e "  [${green}ENABLED${reset}] Automatic display scaling and DPI management enabled."
    else
        set_config_val "auto_scale_mutter" "false"
        set_config_val "auto_dpi_detect" "false"
        set_config_val "manual_dpi" "96"
        echo -e "  [${red}DISABLED${reset}] Automatic display scaling disabled. Standard 96 DPI will be used."
    fi
fi
echo -e "${wine}=============================${reset}"
echo ""

# 3. Asset Validation
echo "Validating installers..."
mkdir -p "$TORQUIO_INSTALLERS_DIR"
SEARCH_DIRS=("$TORQUIO_INSTALLERS_DIR" "$HOME/Downloads" "$PWD")

# Find the highest versioned files across all search directories, matching the install scripts' logic
FOUND_MEDIABAY=$(find "${SEARCH_DIRS[@]}" -maxdepth 1 -type f -name "MediaBay_Installer_win64*.zip" 2>/dev/null | sort -V | tail -n 1)
FOUND_SDA=$(find "${SEARCH_DIRS[@]}" -maxdepth 1 -type f -name "Steinberg_Download_Assistant_*_Installer_win.exe" 2>/dev/null | sort -V | tail -n 1)
FOUND_NP=$(find "${SEARCH_DIRS[@]}" -maxdepth 1 -type f -name "NotePerformer-Installer-*.exe" 2>/dev/null | sort -V | tail -n 1)

MISSING_MANDATORY=false
if [ -z "$FOUND_MEDIABAY" ]; then
    echo -e "  [${red}MISSING${reset}] Mandatory: MediaBay_Installer_win64.zip"
    MISSING_MANDATORY=true
fi
if [ -z "$FOUND_SDA" ]; then
    echo -e "  [${red}MISSING${reset}] Mandatory: Steinberg_Download_Assistant_*_Installer_win.exe"
    MISSING_MANDATORY=true
fi

if [ "$MISSING_MANDATORY" = true ]; then
    echo ""
    echo -e "${red}Error: Mandatory installers were not found.${reset}"
    echo "Please place them in $TORQUIO_INSTALLERS_DIR or ~/Downloads and run this script again."
    exit 1
fi

echo ""
echo -e "${gray}--- Installation Manifest ---${reset}"
echo -e "  [${green}FOUND${reset}] Steinberg MediaBay:           ($(basename "$FOUND_MEDIABAY"))"
echo -e "  [${green}FOUND${reset}] Steinberg Download Assistant: ($(basename "$FOUND_SDA"))"
if [ -n "$FOUND_NP" ]; then
    # Redact the personal user hash from the NotePerformer filename for privacy
    NP_CLEAN_NAME=$(basename "$FOUND_NP" | sed -E 's/(NotePerformer-Installer-[0-9\.]+).*\.exe/\1-[REDACTED].exe/')
    echo -e "  [${green}FOUND${reset}] NotePerformer (3rd Party):    ($NP_CLEAN_NAME)"
else
    echo -e "  [${yellow}SKIP${reset}]  NotePerformer (3rd Party):    Not Found (Skipping)"
fi
echo -e "${gray}-----------------------------${reset}"
echo ""

if [ "$AUTO_ACCEPT" = false ]; then
    read -p "Proceed with the installation? [Y/n]: " confirm
    if [[ "$confirm" =~ ^[Nn]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
fi

# 4. Container Creation
echo "Phase 1: Creating Distrobox container ($TORQUIO_CONTAINER_NAME)..."
if distrobox list | grep -q "$TORQUIO_CONTAINER_NAME"; then
    echo "Container $TORQUIO_CONTAINER_NAME already exists. Skipping creation."
else
    distrobox create -i ubuntu:24.04 -n "$TORQUIO_CONTAINER_NAME" --yes
fi

# We use the absolute path to the workspace within the container. 
# Distrobox mounts the host's current directory to the exact same path in the container.
WORKSPACE_DIR="$SCRIPT_DIR"

# 5. Engine Compilation & Installation
echo "Phase 2: Compiling Wine Engine..."
distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "cd \"$WORKSPACE_DIR\" && ./scripts/1-build/build_wine.sh"

# 6. Prefix Initialization
echo "Phase 3: Initializing Wine Prefix..."
distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "cd \"$WORKSPACE_DIR\" && ./scripts/2-install/setup_prefix.sh"

# 7. Software Component Installation
echo "Phase 4: Installing Steinberg Components..."

echo "Installing MediaBay..."
distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "cd \"$WORKSPACE_DIR\" && ./scripts/2-install/install_mediabay.sh"

echo "Installing SDA..."
distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "cd \"$WORKSPACE_DIR\" && ./scripts/2-install/install_sda.sh"

if [ -n "$FOUND_NP" ]; then
    echo "Installing NotePerformer..."
    distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "cd \"$WORKSPACE_DIR\" && ./scripts/2-install/install_noteperformer.sh"
fi

echo "Extracting Desktop Icons..."
distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "cd \"$WORKSPACE_DIR\" && ./scripts/2-install/extract_icons.sh"

# 8. Host Integration
echo "Phase 5: Performing Host Integration..."
mkdir -p "$HOME/.local/bin"
rm -f "$HOME/.local/bin/torquio" "$HOME/.local/bin/torquio-dorico" "$HOME/.local/bin/torquio-sam" "$HOME/.local/bin/torquio-sda-handler"

echo "Installing torquio orchestrator to ~/.local/bin/torquio..."
ln -s "$SCRIPT_DIR/torquio" "$HOME/.local/bin/torquio"

for handler in "$SCRIPT_DIR/scripts/3-runtime_handlers/"torquio-*; do
    base_name=$(basename "$handler")
    if [ "$base_name" = "torquio-sda-handler" ]; then
        sed "s|@TORQUIO_REPO_DIR@|$SCRIPT_DIR|g" "$handler" > "$HOME/.local/bin/$base_name"
    else
        cp "$handler" "$HOME/.local/bin/"
    fi
done
chmod +x "$HOME/.local/bin/"torquio*

mkdir -p "$HOME/.local/share/applications"

echo "Registering MIME types..."
mkdir -p "$HOME/.local/share/mime/packages"
cp "$SCRIPT_DIR/desktop_stubs/application-x-dorico.xml" "$HOME/.local/share/mime/packages/"
update-mime-database "$HOME/.local/share/mime/"

echo ""
echo "==========================================="
echo "   Software Download Phase                 "
echo "==========================================="
echo "The Steinberg Download Assistant (SDA) is now launching."
echo "You should be able to use it as normal, including the ability to:"
echo "1. Sign in to your Steinberg account in your browser."
echo "2. Install Dorico and any related components."
echo "We recommend using the 'Download All' option." 
echo ""
echo "Opening the Download Assistant..."

# Run the handler in the background so the terminal is not blocked
nohup "$HOME/.local/bin/torquio-sda-handler" > /dev/null 2>&1 &

echo ""
echo "==========================================="
echo "   Torquio Core Setup Complete!            "
echo "==========================================="
echo "You can close this terminal window at any time. Once the "
echo "various components have been installed, remember to run the"
echo "Activation Manager to activate your license."
echo "Happy notating!"
echo "==========================================="
echo ""
