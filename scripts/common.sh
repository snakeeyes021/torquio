#!/bin/bash

# Torquio Common Environment Variables
# This script is sourced by other scripts to ensure consistent paths and settings.

# The name of the Distrobox container
export TORQUIO_CONTAINER_NAME="torquio-env"

# XDG-compliant directories for persistent data and cache
export TORQUIO_DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/torquio"
export TORQUIO_CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/torquio"

# Wine Prefix location
export TORQUIO_PREFIX_DIR="$TORQUIO_DATA_DIR/prefix"

# Wine Build location
export TORQUIO_BUILD_DIR="$TORQUIO_CACHE_DIR/wine-build"

# Installer locations
# If we are running from the repo, we can find the installers directory there.
TORQUIO_REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export TORQUIO_INSTALLERS_DIR="$TORQUIO_REPO_DIR/installers"

# Wine binary paths (usually inside /opt/wine-custom in the container)
export WINE_CUSTOM_PATH="/opt/wine-custom"
export WINE_CUSTOM_BIN="$WINE_CUSTOM_PATH/bin"

# Globally disable winemenubuilder to prevent host desktop pollution
export WINEDLLOVERRIDES="winemenubuilder.exe=d"

# Ensure directories exist
# Note: We don't create the prefix here, as that's handled by wineboot.
# But we ensure the base data and cache dirs exist.
mkdir -p "$TORQUIO_DATA_DIR"
mkdir -p "$TORQUIO_CACHE_DIR"
mkdir -p "$TORQUIO_INSTALLERS_DIR"

# Configuration Helper: Read value from ~/.config/torquio/config.json
get_config_val() {
    local key="$1"
    local default="$2"
    local config_file="$HOME/.config/torquio/config.json"
    if [ ! -f "$config_file" ]; then
        echo "$default"
        return
    fi
    python3 -c "import json; d=json.load(open('$config_file')); v=d.get('$key', '$default'); print(str(v).lower() if isinstance(v, bool) else v)" 2>/dev/null || echo "$default"
}

# Configuration Helper: Write value to ~/.config/torquio/config.json
set_config_val() {
    local key="$1"
    local val="$2"
    local config_file="$HOME/.config/torquio/config.json"
    mkdir -p "$(dirname "$config_file")"
    if [ ! -f "$config_file" ]; then
        echo "{}" > "$config_file"
    fi
    python3 -c "
import json
f = '$config_file'
try:
    d = json.load(open(f))
except Exception:
    d = {}
val = '$val'
if val.lower() == 'true':
    val = True
elif val.lower() == 'false':
    val = False
elif val.isdigit():
    val = int(val)
d['$key'] = val
json.dump(d, open(f, 'w'), indent=4)
" 2>/dev/null || true
}

