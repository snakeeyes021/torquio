#!/bin/bash
set -e

# Valerio Master Installer
# This script automates the entire installation process for Steinberg software on Linux.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/scripts/common.sh"

AUTO_ACCEPT=false
if [[ "$1" == "-y" ]] || [[ "$1" == "--yes" ]]; then
    AUTO_ACCEPT=true
fi

echo "==========================================="
echo "   Valerio: Steinberg on Linux Installer   "
echo "==========================================="
echo ""

# 1. Prerequisite Checks
echo "Checking prerequisites..."
if ! command -v distrobox >/dev/null 2>&1; then
    echo "Error: distrobox is not installed."
    echo "Please install distrobox and either docker or podman."
    exit 1
fi

# Check for docker or podman
if ! command -v docker >/dev/null 2>&1 && ! command -v podman >/dev/null 2>&1; then
    echo "Error: Neither docker nor podman was found."
    echo "Please install one of them to use with distrobox."
    exit 1
fi

# 2. Asset Validation
echo "Validating installers..."
mkdir -p "$VALERIO_INSTALLERS_DIR"
SEARCH_DIRS=("$VALERIO_INSTALLERS_DIR" "$HOME/Downloads" "$PWD")

# Find the highest versioned files across all search directories, matching the install scripts' logic
FOUND_MEDIABAY=$(find "${SEARCH_DIRS[@]}" -maxdepth 1 -type f -name "MediaBay_Installer_win64*.zip" 2>/dev/null | sort -V | tail -n 1)
FOUND_SDA=$(find "${SEARCH_DIRS[@]}" -maxdepth 1 -type f -name "Steinberg_Download_Assistant_*_Installer_win.exe" 2>/dev/null | sort -V | tail -n 1)
FOUND_NP=$(find "${SEARCH_DIRS[@]}" -maxdepth 1 -type f -name "NotePerformer-Installer-*.exe" 2>/dev/null | sort -V | tail -n 1)


MISSING_MANDATORY=false
if [ -z "$FOUND_MEDIABAY" ]; then
    echo "❌ Missing Mandatory: MediaBay_Installer_win64.zip"
    MISSING_MANDATORY=true
fi
if [ -z "$FOUND_SDA" ]; then
    echo "❌ Missing Mandatory: Steinberg_Download_Assistant_*_Installer_win.exe"
    MISSING_MANDATORY=true
fi

if [ "$MISSING_MANDATORY" = true ]; then
    echo ""
    echo "Error: Mandatory installers were not found."
    echo "Please place them in $VALERIO_INSTALLERS_DIR or ~/Downloads and run this script again."
    exit 1
fi

echo ""
echo "--- Installation Manifest ---"
echo "✅ Steinberg MediaBay:           Found ($(basename "$FOUND_MEDIABAY"))"
echo "✅ Steinberg Download Assistant: Found ($(basename "$FOUND_SDA"))"
if [ -n "$FOUND_NP" ]; then
    # Redact the personal user hash from the NotePerformer filename for privacy
    NP_CLEAN_NAME=$(basename "$FOUND_NP" | sed -E 's/(NotePerformer-Installer-[0-9\.]+).*\.exe/\1-[REDACTED].exe/')
    echo "✅ NotePerformer (3rd Party):    Found ($NP_CLEAN_NAME)"
else
    echo "⚠️ NotePerformer (3rd Party):    Not Found (Skipping)"
fi
echo "-----------------------------"
echo ""

if [ "$AUTO_ACCEPT" = false ]; then
    read -p "Proceed with the installation? [Y/n] " confirm
    if [[ "$confirm" =~ ^[Nn]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
fi

# 3. Container Creation
echo "Phase 1: Creating Distrobox container ($VALERIO_CONTAINER_NAME)..."
if distrobox list | grep -q "$VALERIO_CONTAINER_NAME"; then
    echo "Container $VALERIO_CONTAINER_NAME already exists. Skipping creation."
else
    distrobox create -i ubuntu:24.04 -n "$VALERIO_CONTAINER_NAME" --yes
fi

# We use the absolute path to the workspace within the container. 
# Distrobox mounts the host's current directory to the exact same path in the container.
WORKSPACE_DIR="$(pwd)"

# 4. Engine Compilation & Installation
echo "Phase 2: Compiling Wine Engine..."
distrobox enter "$VALERIO_CONTAINER_NAME" -- bash -c "cd \"$WORKSPACE_DIR\" && ./scripts/1-build/build_wine.sh"

# 5. Prefix Initialization
echo "Phase 3: Initializing Wine Prefix..."
distrobox enter "$VALERIO_CONTAINER_NAME" -- bash -c "cd \"$WORKSPACE_DIR\" && ./scripts/2-install/setup_prefix.sh"

# 6. Software Component Installation
echo "Phase 4: Installing Steinberg Components..."

echo "Installing MediaBay..."
distrobox enter "$VALERIO_CONTAINER_NAME" -- bash -c "cd \"$WORKSPACE_DIR\" && ./scripts/2-install/install_mediabay.sh"

echo "Installing SDA..."
distrobox enter "$VALERIO_CONTAINER_NAME" -- bash -c "cd \"$WORKSPACE_DIR\" && ./scripts/2-install/install_sda.sh"

if [ -n "$FOUND_NP" ]; then
    echo "Installing NotePerformer..."
    distrobox enter "$VALERIO_CONTAINER_NAME" -- bash -c "cd \"$WORKSPACE_DIR\" && ./scripts/2-install/install_noteperformer.sh"
fi

echo "Extracting Desktop Icons..."
distrobox enter "$VALERIO_CONTAINER_NAME" -- bash -c "cd \"$WORKSPACE_DIR\" && ./scripts/2-install/extract_icons.sh"

# 7. Host Integration
echo "Phase 5: Performing Host Integration..."
mkdir -p "$HOME/.local/bin"
for handler in "$SCRIPT_DIR/scripts/3-runtime_handlers/"*.sh; do
    base_name=$(basename "$handler")
    if [ "$base_name" = "steinberg-sda-handler.sh" ]; then
        sed "s|@VALERIO_REPO_DIR@|$SCRIPT_DIR|g" "$handler" > "$HOME/.local/bin/$base_name"
    else
        cp "$handler" "$HOME/.local/bin/"
    fi
done
chmod +x "$HOME/.local/bin/"*.sh

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
nohup "$HOME/.local/bin/steinberg-sda-handler.sh" > /dev/null 2>&1 &

echo ""
echo "==========================================="
echo "   Valerio Core Setup Complete!            "
echo "==========================================="
echo "You can close this terminal window at any time. Once the "
echo "various components have been installed, remember to run the"
echo "Activation Manager to activate your license."
echo "Happy notating!"
echo "==========================================="
echo ""
