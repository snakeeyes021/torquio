#!/bin/bash
set -e

CACHE_DIR="$HOME/.cache/valerio-installers"
# Array of directories to search. Order matters: it will stop at the first match.
SEARCH_DIRS=("$HOME/Downloads" "$CACHE_DIR" "$(pwd)")
FOUND_INSTALLER=""

# 1. Search Phase
for DIR in "${SEARCH_DIRS[@]}"; do
    # Skip if the directory doesn't exist
    if [ ! -d "$DIR" ]; then
        continue
    fi
    
    # Look for the Cantai installer in this directory
    # Using find is a bit safer than ls for getting absolute paths and handling weird characters
    MATCH=$(find "$DIR" -maxdepth 1 -name "Cantai-Windows-Dorico-Installer-*.exe" | head -n 1)
    
    if [ -n "$MATCH" ]; then
        FOUND_INSTALLER="$MATCH"
        echo "Found Cantai installer: $FOUND_INSTALLER"
        break
    fi
done

# 2. Download / Fallback Phase
if [ -z "$FOUND_INSTALLER" ]; then
    echo "Error: Cantai installer not found locally."
    echo "Please download the installer and place it in ~/Downloads, or run this script from the directory containing it."
    
    # ==============================================================================
    # FUTURE AUTOMATION SKELETON:
    # 
    # mkdir -p "$CACHE_DIR"
    # echo "Downloading Cantai installer to cache..."
    # 
    # # Example using wget:
    # # wget -q --show-progress "https://api.example.com/downloads/cantai/latest" -O "$CACHE_DIR/Cantai-Installer-Latest.exe"
    # 
    # # Example using curl:
    # # curl -L "https://api.example.com/downloads/cantai/latest" -o "$CACHE_DIR/Cantai-Installer-Latest.exe"
    # 
    # FOUND_INSTALLER="$CACHE_DIR/Cantai-Installer-Latest.exe"
    # ==============================================================================

    exit 1
fi

# 3. Execution Phase
# Passing the guaranteed absolute path ($FOUND_INSTALLER) to Wine inside the Distrobox container.
distrobox enter dorico-box -- bash -c "export WINEPREFIX=\"\$HOME/dev/steinberg-on-linux/dorico-prefix\"; export PATH=\"/opt/wine-custom/bin:\$PATH\"; wine \"$FOUND_INSTALLER\""
