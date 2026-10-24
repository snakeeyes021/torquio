#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

# Array of directories to search. Order matters: it will stop at the first match.
SEARCH_DIRS=("$TORQUIO_INSTALLERS_DIR" "$HOME/Downloads" "$(pwd)")
FOUND_INSTALLER=""

# 1. Search Phase
echo "Searching for Cantai installer..."
# Cantai's download is a zip (e.g. Cantai-Windows-Installer-v3.1.1.exe.zip) holding the setup program
# (e.g. CantaiLocalRenderVST-3.1.1-Setup.exe). Pick the highest version found.
FOUND_INSTALLER=$(find "${SEARCH_DIRS[@]}" -maxdepth 1 -type f -name "Cantai-Windows-*Installer-*.exe.zip" 2>/dev/null | sort -V | tail -n 1)

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

EXTRACTED_EXE=$(find "$TMP_DIR" -type f -iname "*.exe" | head -n 1)

if [ -z "$EXTRACTED_EXE" ]; then
    echo "Error: No setup program found in $FOUND_INSTALLER"
    exit 1
fi

# 4. Execution Phase
# Cantai's setup is Inno Setup: install silently unless --interactive is given, and fall back to the
# wizard if the silent install didn't leave the plug-in and its renderer in place.
run_setup() {
    distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "export WINEPREFIX=\"$TORQUIO_PREFIX_DIR\"; export PATH=\"$WINE_CUSTOM_BIN:\$PATH\"; export WINEDLLOVERRIDES=\"winemenubuilder.exe=d\"; wine \"$EXTRACTED_EXE\" $*" || true
}
cantai_installed() {
    ls "$TORQUIO_PREFIX_DIR"/drive_c/users/*/AppData/Local/Programs/Common/VST3/Cantai.vst3 >/dev/null 2>&1 &&
        find "$TORQUIO_PREFIX_DIR"/drive_c/users/*/AppData/Local/"Cantai Local Render" -maxdepth 1 -iname cantai.exe 2>/dev/null | grep -q .
}
if [[ "$1" == "--interactive" ]]; then
    echo "Launching the Cantai installer..."
    run_setup
else
    echo "Installing Cantai silently (this takes a minute or two)..."
    run_setup /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-
    if ! cantai_installed; then
        echo "The silent install didn't complete; opening Cantai's installer so you can finish it..."
        run_setup
    fi
fi
if ! cantai_installed; then
    echo "Error: Cantai doesn't appear to be installed."
    exit 1
fi

# Cantai installs into the per-user VST3 folder, which Dorico's audio engine doesn't scan; link it
# into the system-wide one (the Dorico launcher also does this for any per-user plug-in).
COMMON_VST3="$TORQUIO_PREFIX_DIR/drive_c/Program Files/Common Files/VST3"
for USER_VST3 in "$TORQUIO_PREFIX_DIR"/drive_c/users/*/AppData/Local/Programs/Common/VST3/*.vst3; do
    [ -e "$USER_VST3" ] || continue
    if [ ! -e "$COMMON_VST3/$(basename "$USER_VST3")" ]; then
        mkdir -p "$COMMON_VST3"
        ln -s "$USER_VST3" "$COMMON_VST3/$(basename "$USER_VST3")"
    fi
done

# Cantai's editor is a web view; provision the WebView2 runtime it needs.
"$SCRIPT_DIR/install_webview2.sh"

# Cantai's renderer runs part of its model on the GPU when it has vkd3d-proton (the Dorico launcher sets
# it up and picks the GPU).
"$SCRIPT_DIR/install_vkd3d_proton.sh" || echo "Couldn't fetch vkd3d-proton; Cantai will render on the CPU."
