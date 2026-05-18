#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

export WINEPREFIX="$VALERIO_PREFIX_DIR"
export WINE="$WINE_CUSTOM_BIN/wine"
export WINESERVER="$WINE_CUSTOM_BIN/wineserver"
export PATH="$WINE_CUSTOM_BIN:$PATH"

echo "Looking for MediaBay installer..."
# Search locations for the zip
SEARCH_DIRS=("$VALERIO_INSTALLERS_DIR" "$HOME/Downloads" "$(pwd)")
FOUND_ZIP=""

for DIR in "${SEARCH_DIRS[@]}"; do
    if [ -f "$DIR/MediaBay_Installer_win64.zip" ]; then
        FOUND_ZIP="$DIR/MediaBay_Installer_win64.zip"
        break
    fi
done

if [ -z "$FOUND_ZIP" ]; then
    echo "Error: MediaBay_Installer_win64.zip not found in search locations."
    echo "Please place it in $VALERIO_INSTALLERS_DIR or ~/Downloads."
    exit 1
fi

echo "Found MediaBay installer: $FOUND_ZIP"
echo "Extracting MediaBay..."
mkdir -p "$VALERIO_DATA_DIR/MediaBay_extracted"
unzip -o "$FOUND_ZIP" -d "$VALERIO_DATA_DIR/MediaBay_extracted"

echo "Performing recursive cleanup of blocked files (preinstall.ps1)..."
# Find and remove any preinstall.ps1 scripts recursively within the extracted folder
# These often cause "Not Trusted" errors during installation
find "$VALERIO_DATA_DIR/MediaBay_extracted" -name "preinstall.ps1" -delete

echo "Executing MediaBay Setup.exe..."
# MediaBay zip usually extracts into a folder like "MediaBay_1.3.60_Installer_win64"
# We find the Setup.exe within the extracted directory.
SETUP_EXE=$(find "$VALERIO_DATA_DIR/MediaBay_extracted" -name "Setup.exe" | head -n 1)

if [ -n "$SETUP_EXE" ]; then
    if [[ "$1" == "--interactive" ]]; then
        echo "Running interactively: wine $SETUP_EXE"
        wine "$SETUP_EXE" || true
    else
        echo "Running silently: wine $SETUP_EXE --silent"
        wine "$SETUP_EXE" --silent || true
    fi
else
    echo "Error: Could not find Setup.exe in the extracted MediaBay folder."
    exit 1
fi

echo "MediaBay installation complete!"
