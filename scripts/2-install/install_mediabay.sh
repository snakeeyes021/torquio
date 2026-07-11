#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

export WINEPREFIX="$TORQUIO_PREFIX_DIR"
export WINE="$WINE_CUSTOM_BIN/wine"
export WINESERVER="$WINE_CUSTOM_BIN/wineserver"
export PATH="$WINE_CUSTOM_BIN:$PATH"

echo "Looking for MediaBay installers..."
# Search locations for the zip
SEARCH_DIRS=("$TORQUIO_INSTALLERS_DIR" "$HOME/Downloads" "$(pwd)")
mapfile -t ZIPS < <(find "${SEARCH_DIRS[@]}" -maxdepth 1 -type f -name "MediaBay_Installer_win64*.zip" 2>/dev/null)

if [ ${#ZIPS[@]} -eq 0 ]; then
    echo "Error: MediaBay installer zip not found in search locations."
    echo "Please place MediaBay_Installer_win64.zip in $TORQUIO_INSTALLERS_DIR or ~/Downloads."
    exit 1
fi

echo "Clearing previous extraction directory..."
rm -rf "$TORQUIO_DATA_DIR/MediaBay_extracted"
mkdir -p "$TORQUIO_DATA_DIR/MediaBay_extracted"

for ZIP in "${ZIPS[@]}"; do
    echo "Extracting: $ZIP"
    unzip -o "$ZIP" -d "$TORQUIO_DATA_DIR/MediaBay_extracted"
done

echo "Performing recursive cleanup of blocked files (preinstall.ps1)..."
# Find and remove any preinstall.ps1 scripts recursively within the extracted folder
# These often cause "Not Trusted" errors during installation
find "$TORQUIO_DATA_DIR/MediaBay_extracted" -name "preinstall.ps1" -delete

echo "Identifying highest versioned installer..."
# Find all directories containing Setup.exe and pick the one that is "highest" via version sort.
# This ensures we pick e.g. "MediaBay 1.3.70" over "MediaBay 1.3.60" regardless of file dates.
BEST_FOLDER=$(find "$TORQUIO_DATA_DIR/MediaBay_extracted" -name "Setup.exe" -printf "%h\n" | sort -V | tail -n 1)

if [ -n "$BEST_FOLDER" ]; then
    SETUP_EXE="$BEST_FOLDER/Setup.exe"
    echo "Selected versioned folder: $(basename "$BEST_FOLDER")"
    if [[ "$1" == "--interactive" ]]; then
        echo "Running interactively: wine $SETUP_EXE"
        wine "$SETUP_EXE" || true
    else
        echo "Running silently: wine $SETUP_EXE --silent"
        wine "$SETUP_EXE" --silent || true
    fi
else
    echo "Error: Could not find Setup.exe in any extracted MediaBay folder."
    exit 1
fi

echo "MediaBay installation complete!"
