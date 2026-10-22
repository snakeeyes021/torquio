#!/bin/bash
# Provision a private copy of Microsoft's WebView2 runtime in the Dorico prefix. It's needed by
# plug-ins with web-based editors (e.g. Cantai). The runtime is installed into a throwaway prefix and
# only its application folder is copied over, so the Dorico prefix doesn't get Edge's update services.
# WEBVIEW2_BROWSER_EXECUTABLE_FOLDER is set in the prefix's HKCU\Environment, which Wine applies to
# every process, so it works however Dorico is launched.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

WEBVIEW2_URL="https://go.microsoft.com/fwlink/?linkid=2124701"  # Evergreen standalone installer, x64
WEBVIEW2_CACHE="$TORQUIO_CACHE_DIR/webview2"
INSTALLER="$WEBVIEW2_CACHE/MicrosoftEdgeWebView2RuntimeInstallerX64.exe"
SCRATCH_PREFIX="$WEBVIEW2_CACHE/prefix"
DEST_ROOT="$TORQUIO_PREFIX_DIR/drive_c/Program Files/Torquio/WebView2"

set_environment() {
    local version
    version=$(basename "$(ls -d "$DEST_ROOT"/*/ | sort -V | tail -n 1)")
    echo "Pointing the Dorico prefix at WebView2 $version..."
    distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "export WINEPREFIX=\"$TORQUIO_PREFIX_DIR\"; export PATH=\"$WINE_CUSTOM_BIN:\$PATH\"; export WINEDEBUG=-all; wine reg add 'HKCU\\Environment' /v WEBVIEW2_BROWSER_EXECUTABLE_FOLDER /t REG_SZ /d 'C:\\Program Files\\Torquio\\WebView2\\$version' /f" >/dev/null
}

if [ "$1" != "--force" ] && ls "$DEST_ROOT"/*/msedgewebview2.exe >/dev/null 2>&1; then
    echo "WebView2 runtime already provisioned in $DEST_ROOT."
    set_environment
    exit 0
fi

mkdir -p "$WEBVIEW2_CACHE"
if [ ! -f "$INSTALLER" ]; then
    echo "Downloading the WebView2 runtime from Microsoft (~200 MB)..."
    curl -fL --progress-bar -o "$INSTALLER.part" "$WEBVIEW2_URL"
    mv "$INSTALLER.part" "$INSTALLER"
fi

echo "Installing the WebView2 runtime into a temporary prefix..."
rm -rf "$SCRATCH_PREFIX"
distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "export WINEPREFIX=\"$SCRATCH_PREFIX\"; export PATH=\"$WINE_CUSTOM_BIN:\$PATH\"; export WINEDEBUG=-all; export WINEDLLOVERRIDES='mscoree=;mshtml='; wineboot -i >/dev/null 2>&1; wine \"$INSTALLER\" /silent /install; wineserver -k" || true

APP_DIR=$(ls -d "$SCRATCH_PREFIX/drive_c/Program Files (x86)/Microsoft/EdgeWebView/Application"/[0-9]*/ 2>/dev/null | sort -V | tail -n 1)
if [ -z "$APP_DIR" ] || [ ! -f "${APP_DIR}msedgewebview2.exe" ]; then
    echo "Error: the WebView2 runtime installation failed."
    rm -rf "$SCRATCH_PREFIX"
    exit 1
fi

echo "Copying WebView2 $(basename "$APP_DIR") into the Dorico prefix..."
mkdir -p "$DEST_ROOT"
rm -rf "${DEST_ROOT:?}"/*
cp -a "${APP_DIR%/}" "$DEST_ROOT/"
rm -rf "$SCRATCH_PREFIX"
set_environment
echo "WebView2 runtime provisioned."
