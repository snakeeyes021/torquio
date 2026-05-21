#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

export WINEPREFIX="$VALERIO_PREFIX_DIR"
export WINE="$WINE_CUSTOM_BIN/wine"
export WINESERVER="$WINE_CUSTOM_BIN/wineserver"
export PATH="$WINE_CUSTOM_BIN:$PATH"

# Array of directories to search. Order matters: it will stop at the first match.
SEARCH_DIRS=("$VALERIO_INSTALLERS_DIR" "$HOME/Downloads" "$(pwd)")
FOUND_INSTALLER=""

# 1. Search Phase
echo "Searching for Steinberg Download Assistant installer..."
# Find all matching installers across all search directories, sort them by version, and pick the highest
FOUND_INSTALLER=$(find "${SEARCH_DIRS[@]}" -maxdepth 1 -type f -name "Steinberg_Download_Assistant_*_Installer_win.exe" 2>/dev/null | sort -V | tail -n 1)

if [ -n "$FOUND_INSTALLER" ]; then
    echo "Found SDA installer: $FOUND_INSTALLER"
fi

# 2. Download / Fallback Phase
if [ -z "$FOUND_INSTALLER" ]; then
    echo "Error: Steinberg Download Assistant installer not found."
    echo "Please download the Windows installer from Steinberg's website and place it in:"
    echo "  - $VALERIO_INSTALLERS_DIR"
    echo "  - ~/Downloads"
    echo ""
    echo "Filename should match: Steinberg_Download_Assistant_*_Installer_win.exe"
    exit 1
fi

# 3. Execution Phase
if [[ "$1" == "--interactive" ]]; then
    echo "Launching SDA installer interactively..."
    wine "$FOUND_INSTALLER" || true
else
    echo "Installing SDA silently..."
    wine "$FOUND_INSTALLER" --mode unattended || true
fi

# 4. Cleanup Phase
# The SDA installer automatically launches background daemons (e.g., STEI~B2R.EXE, aria2c.exe) 
# which lock the Wine prefix and cause subsequent installations (like NotePerformer) to hang.
# We explicitly kill the prefix here to release all locks before the script moves on.
echo "Cleaning up SDA background processes..."
"$WINESERVER" -k || true
