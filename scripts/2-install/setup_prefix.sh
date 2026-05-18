#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

export WINEPREFIX="$VALERIO_PREFIX_DIR"
export WINE="$WINE_CUSTOM_BIN/wine"
export WINESERVER="$WINE_CUSTOM_BIN/wineserver"
export PATH="$WINE_CUSTOM_BIN:$PATH"

# Suppress Wine Mono, Gecko installer prompts, and prevent winemenubuilder pollution
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES};mscoree=d;mshtml=d"

if [ -d "$WINEPREFIX" ] && [ -f "$WINEPREFIX/.valerio_core_installed" ]; then
    echo "Wine prefix already initialized with core dependencies. Skipping baseline setup."
    exit 0
fi

echo "Initializing Wine prefix at $WINEPREFIX..."
wineboot -u

echo "Installing winetricks dependencies (this may pop up some windows, please click through them if needed)..."
winetricks -q d3dx9 msls31 allfonts d3dcompiler_43 d3dcompiler_47 vcrun2019 dotnet48 win10

echo "Downloading and installing wine-icu (required for Dorico)..."
ICU_VERSION="72.1"
ICU_X86_URL="https://gitlab.winehq.org/api/v4/projects/2302/packages/generic/wine-icu/$ICU_VERSION/wine-icu-$ICU_VERSION-x86.msi"
ICU_X64_URL="https://gitlab.winehq.org/api/v4/projects/2302/packages/generic/wine-icu/$ICU_VERSION/wine-icu-$ICU_VERSION-x86_64.msi"

mkdir -p "$VALERIO_CACHE_DIR/icu"
wget -q --show-progress "$ICU_X86_URL" -O "$VALERIO_CACHE_DIR/icu/wine-icu-x86.msi"
wget -q --show-progress "$ICU_X64_URL" -O "$VALERIO_CACHE_DIR/icu/wine-icu-x64.msi"

echo "Installing ICU x86..."
wine msiexec /i "$VALERIO_CACHE_DIR/icu/wine-icu-x86.msi" /qn
echo "Installing ICU x64..."
wine msiexec /i "$VALERIO_CACHE_DIR/icu/wine-icu-x64.msi" /qn

# Drop a marker file to indicate the prefix setup completed successfully
touch "$WINEPREFIX/.valerio_core_installed"
echo "Done with winetricks and ICU installation!"