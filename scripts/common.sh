#!/bin/bash

# Torquio Common Environment Variables
# This script is sourced by other scripts to ensure consistent paths and settings.

# The name of the Distrobox container
export TORQUIO_CONTAINER_NAME="${TORQUIO_CONTAINER_NAME:-torquio-env}"

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

# Torquio's prebuilt container image (scripts/1-build/Containerfile, published by GitHub Actions). Each
# build is tagged with the git tree hash of scripts/1-build, so a copy of Torquio always finds the image
# built from exactly its own Wine build files.
export TORQUIO_IMAGE_REPO="${TORQUIO_IMAGE_REPO:-ghcr.io/snakeeyes021/torquio-env}"

# The prebuilt image matching this copy of Torquio; prints nothing when Wine has to be compiled locally
# (not a git checkout, local changes to the Wine build files, or "build_from_source" set in the config).
torquio_prebuilt_image() {
    [ "$(get_config_val "build_from_source" "false")" = "true" ] && return
    [ -z "$(git -C "$TORQUIO_REPO_DIR" status --porcelain -- scripts/1-build 2>/dev/null)" ] || return 0
    local tree
    tree=$(git -C "$TORQUIO_REPO_DIR" rev-parse HEAD:scripts/1-build 2>/dev/null) || return 0
    echo "$TORQUIO_IMAGE_REPO:build-${tree:0:12}"
}

# The machine ID Torquio gives its container (scripts/1-build/container_gpu_setup.sh): derived from the host's,
# hashed. Wine turns it into the Windows system UUID, which some plug-ins (e.g. Cantai) tie their license to.
torquio_derived_machine_id() {
    [ -s /etc/machine-id ] || return 0
    printf 'torquio:%s' "$(cat /etc/machine-id)" | sha256sum | cut -c1-32
}

# The container engine distrobox uses (it prefers podman)
torquio_container_manager() {
    if [ -n "$DBX_CONTAINER_MANAGER" ]; then echo "$DBX_CONTAINER_MANAGER"
    elif command -v podman >/dev/null 2>&1; then echo podman
    else echo docker; fi
}

# Download a prebuilt image unless it's already here (a build tag's contents never change)
torquio_pull_image() {
    local mgr
    mgr=$(torquio_container_manager)
    "$mgr" image inspect "$1" >/dev/null 2>&1 || "$mgr" pull "$1"
}

# The image the Torquio container was created from
torquio_container_image() {
    local mgr
    mgr=$(torquio_container_manager)
    if [ "$mgr" = podman ]; then
        podman container inspect --format '{{.ImageName}}' "$TORQUIO_CONTAINER_NAME" 2>/dev/null || true
    else
        docker container inspect --format '{{.Config.Image}}' "$TORQUIO_CONTAINER_NAME" 2>/dev/null || true
    fi
}

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
    python3 -c 'import sys, json; d=json.load(open(sys.argv[1])); v=d.get(sys.argv[2], sys.argv[3]); print(str(v).lower() if isinstance(v, bool) else v)' "$config_file" "$key" "$default" 2>/dev/null || echo "$default"
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
    python3 -c '
import sys, json
f = sys.argv[1]
key = sys.argv[2]
val = sys.argv[3]
try:
    d = json.load(open(f))
except Exception:
    d = {}
if val.lower() == "true":
    val = True
elif val.lower() == "false":
    val = False
elif val.isdigit():
    val = int(val)
d[key] = val
json.dump(d, open(f, "w"), indent=4)
' "$config_file" "$key" "$val" 2>/dev/null || true
}

get_xwayland_scaling_factor() {
    local val=$(gsettings get org.gnome.mutter.wayland xwayland-scaling-factor 2>/dev/null | awk '{print $NF}')
    if [ -z "$val" ]; then
        val=$(gsettings get org.gnome.mutter xwayland-scaling-factor 2>/dev/null | awk '{print $NF}')
    fi
    echo "$val" | tr -d ' ' | cut -d'.' -f1 | tr -cd '0-9'
}

