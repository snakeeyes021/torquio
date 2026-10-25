#!/bin/bash

# Torquio Common Environment Variables
# Sourced by the container's scripts and by the installer and uninstaller wrappers (install.sh, cleanup.sh).
# Torquio's Python code has the same locations in lib/torquio/paths.py.

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

# Globally disable winemenubuilder to prevent host desktop pollution
export WINEDLLOVERRIDES="winemenubuilder.exe=d"

# Ensure directories exist
# Note: We don't create the prefix here, as that's handled by wineboot.
# But we ensure the base data and cache dirs exist.
mkdir -p "$TORQUIO_DATA_DIR"
mkdir -p "$TORQUIO_CACHE_DIR"
mkdir -p "$TORQUIO_INSTALLERS_DIR"

# The installer and uninstaller wrappers run Torquio's Python code through this: torquio_py install|uninstall
# (lib/torquio/__main__.py).
torquio_py() {
    python3 "$TORQUIO_REPO_DIR/lib/torquio_bridge.py" "$@"
}

# Torquio needs Python 3.9 or newer on the host. install.sh and cleanup.sh check before anything uses it (the
# torquio entry point checks itself); not done on sourcing, because the container's scripts source this file too.
torquio_require_python() {
    local version
    if ! version=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null); then
        echo "Torquio needs Python 3.9 or newer, and python3 wasn't found; install your distribution's python3 package." >&2
        exit 1
    fi
    if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
        echo "Torquio needs Python 3.9 or newer (yours is $version); install a newer python3 package." >&2
        exit 1
    fi
}
