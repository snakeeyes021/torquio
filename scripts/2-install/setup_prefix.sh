#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

export WINEPREFIX="$TORQUIO_PREFIX_DIR"
export WINE="$WINE_CUSTOM_BIN/wine"
export WINESERVER="$WINE_CUSTOM_BIN/wineserver"
export PATH="$WINE_CUSTOM_BIN:$PATH"

# Suppress Wine Mono, Gecko installer prompts, and prevent winemenubuilder pollution
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES};mscoree=d;mshtml=d"

if [ -d "$WINEPREFIX" ] && [ -f "$WINEPREFIX/.torquio_core_installed" ]; then
    echo "Wine prefix already initialized with core dependencies. Skipping baseline setup."
    exit 0
fi

echo "Initializing Wine prefix at $WINEPREFIX..."
wineboot -u

echo "Installing winetricks dependencies (this may pop up some windows, please click through them if needed)..."
winetricks -q d3dx9 msls31 allfonts d3dcompiler_43 d3dcompiler_47 vcrun2019 dotnet48 win10

echo "Configuring Keyboard Focus Loss Mitigation & Accessibility Registry Overrides..."
# FocusOnClick forces window focus acquisition upon mouse click, preventing focus loss in modals
wine reg add "HKCU\\Software\\Wine\\X11 Driver" /v FocusOnClick /t REG_SZ /d Y /f
wine reg add "HKCU\\Software\\Wine\\X11 Driver" /v UseTakeFocus /t REG_SZ /d N /f

# Force client-side font anti-aliasing and XRender overrides in Wine X11 Driver
wine reg add "HKCU\\Software\\Wine\\X11 Driver" /v ClientSideWithRender /t REG_SZ /d Y /f
wine reg add "HKCU\\Software\\Wine\\X11 Driver" /v ClientSideAntiAliasWithRender /t REG_SZ /d Y /f
wine reg add "HKCU\\Software\\Wine\\X11 Driver" /v ClientSideWithCore /t REG_SZ /d Y /f

# Enable Font Smoothing (ClearType) and subpixel rendering parameters
wine reg add "HKCU\\Control Panel\\Desktop" /v FontSmoothing /t REG_SZ /d 2 /f
wine reg add "HKCU\\Control Panel\\Desktop" /v FontSmoothingGamma /t REG_DWORD /d 1400 /f
wine reg add "HKCU\\Control Panel\\Desktop" /v FontSmoothingOrientation /t REG_DWORD /d 1 /f
wine reg add "HKCU\\Control Panel\\Desktop" /v FontSmoothingType /t REG_DWORD /d 2 /f

# Customize key repeat speed to mitigate Auto-Repeat Lag Bug
wine reg add "HKCU\\Control Panel\\Accessibility\\Keyboard Response" /v AutoRepeatDelay /t REG_SZ /d "250" /f
wine reg add "HKCU\\Control Panel\\Accessibility\\Keyboard Response" /v AutoRepeatRate /t REG_SZ /d "30" /f
wine reg add "HKCU\\Control Panel\\Accessibility\\Keyboard Response" /v Flags /t REG_SZ /d "126" /f

echo "Downloading and installing wine-icu (required for Dorico)..."
ICU_VERSION="72.1"
ICU_X86_URL="https://gitlab.winehq.org/api/v4/projects/2302/packages/generic/wine-icu/$ICU_VERSION/wine-icu-$ICU_VERSION-x86.msi"
ICU_X64_URL="https://gitlab.winehq.org/api/v4/projects/2302/packages/generic/wine-icu/$ICU_VERSION/wine-icu-$ICU_VERSION-x86_64.msi"

mkdir -p "$TORQUIO_CACHE_DIR/icu"
wget -q --show-progress "$ICU_X86_URL" -O "$TORQUIO_CACHE_DIR/icu/wine-icu-x86.msi"
wget -q --show-progress "$ICU_X64_URL" -O "$TORQUIO_CACHE_DIR/icu/wine-icu-x64.msi"

echo "Installing ICU x86..."
wine msiexec /i "$TORQUIO_CACHE_DIR/icu/wine-icu-x86.msi" /qn
echo "Installing ICU x64..."
wine msiexec /i "$TORQUIO_CACHE_DIR/icu/wine-icu-x64.msi" /qn

# Drop a marker file to indicate the prefix setup completed successfully
touch "$WINEPREFIX/.torquio_core_installed"
echo "Done with winetricks, ICU, and registry optimization!"