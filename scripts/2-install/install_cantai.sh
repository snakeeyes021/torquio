#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

# Array of directories to search. Order matters: it will stop at the first match.
SEARCH_DIRS=("$TORQUIO_INSTALLERS_DIR" "$HOME/Downloads" "$(pwd)")
FOUND_INSTALLER=""

# 1. Search Phase
echo "Searching for Cantai installer..."
# Find all matching installers across all search directories, sort them by version, and pick the highest
FOUND_INSTALLER=$(find "${SEARCH_DIRS[@]}" -maxdepth 1 -type f -name "Cantai-Windows-Dorico-Installer-*.exe.zip" 2>/dev/null | sort -V | tail -n 1)

if [ -n "$FOUND_INSTALLER" ]; then
    echo "Found Cantai installer: $FOUND_INSTALLER"
fi

# 2. Download / Fallback Phase
if [ -z "$FOUND_INSTALLER" ]; then
    echo "Error: Cantai installer not found locally."
    echo "Please download the installer and place it in $TORQUIO_INSTALLERS_DIR, ~/Downloads, or run this script from the directory containing it."
    
    exit 1
fi

# 3. Extraction Phase
echo "Extracting Cantai archive..."
TMP_DIR=$(mktemp -d)
# Ensure the temporary directory is cleaned up upon script exit or failure
trap 'rm -rf "$TMP_DIR"' EXIT

unzip -q "$FOUND_INSTALLER" -d "$TMP_DIR"

# The zip creates a directory named identically to the executable, containing the executable itself
EXE_NAME=$(basename "$FOUND_INSTALLER" .zip)
EXTRACTED_EXE="$TMP_DIR/$EXE_NAME/$EXE_NAME"

if [ ! -f "$EXTRACTED_EXE" ]; then
    echo "Error: Failed to find the extracted executable at $EXTRACTED_EXE"
    exit 1
fi

# 4. Execution Phase
if [[ "$1" == "--interactive" ]]; then
    echo "Launching Cantai installer interactively..."
    # Passing the guaranteed absolute path ($EXTRACTED_EXE) to Wine inside the Distrobox container.
    distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "export WINEPREFIX=\"$TORQUIO_PREFIX_DIR\"; export PATH=\"$WINE_CUSTOM_BIN:\$PATH\"; wine \"$EXTRACTED_EXE\"" || true
else
    echo "Installing Cantai silently..."
    # TODO: Replace the active command below with the correct silent installation flag once identified.
    # It will likely look something like this:
    # distrobox enter "$VALERIO_CONTAINER_NAME" -- bash -c "export WINEPREFIX=\"$VALERIO_PREFIX_DIR\"; export PATH=\"$WINE_CUSTOM_BIN:\$PATH\"; wine \"$EXTRACTED_EXE\" /S" || true
    
    distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "export WINEPREFIX=\"$TORQUIO_PREFIX_DIR\"; export PATH=\"$WINE_CUSTOM_BIN:\$PATH\"; wine \"$EXTRACTED_EXE\"" || true
fi