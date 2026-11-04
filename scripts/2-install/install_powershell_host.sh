#!/bin/bash
# Build Torquio's stand-in for Windows PowerShell's hosting library (powershell_host/, see the top of its source)
# and install it into the prefix's GAC, so Steinberg's Install Assistant can run MediaBay's pre-install step and
# install MediaBay updates itself (docs/MEDIABAY_UPDATES.md). Built in the prefix with the compiler of its .NET
# Framework 4.8 (winetricks dotnet48), so nothing prebuilt is shipped. Runs from setup_prefix.sh: during prefix
# setup, after Update Torquio and from the menu's Fix Icons & Refresh Launchers; does nothing when the installed
# copy is already built from this source.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

export WINEPREFIX="$TORQUIO_PREFIX_DIR"
export WINE="$WINE_CUSTOM_BIN/wine"
export WINESERVER="$WINE_CUSTOM_BIN/wineserver"
export PATH="$WINE_CUSTOM_BIN:$PATH"
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES};winemenubuilder.exe=d"

NAME="System.Management.Automation"
SOURCE="$SCRIPT_DIR/powershell_host/$NAME.cs"
# The identity programs built against Windows PowerShell reference: Version=3.0.0.0, PublicKeyToken=31bf3856ad364e35
GAC_DIR="$WINEPREFIX/drive_c/windows/Microsoft.NET/assembly/GAC_MSIL/$NAME/v4.0_3.0.0.0__31bf3856ad364e35"
CSC="$WINEPREFIX/drive_c/windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe"
MARKER="$WINEPREFIX/.torquio_powershell_host"
TAG="torquio-powershell-host"  # in the assembly's informational version, to recognise our own copy

# The public key whose token is 31bf3856ad364e35 (a public identity: Mono's WindowsBase.dll carries the same key).
# Only the public key: the assembly is delay-signed, which the .NET 4 GAC loads without a signature check.
PUBLIC_KEY="ACQAAASAAACUAAAABgIAAAAkAABSU0ExAAQAAAEAAQC1/JDnAn9nhx53Oo/eiTjIHdQCumW5IB1gWT6WxJJlHoicwT8UFeu1P6wRMa4L0zPF7mAhZy2XGOoxqK69DaAHLyXYfbpvyQ/9WY7U2jXkTDmMRUMH6OM7hCYUPa7J9ZaDb5fI90dQ5ZdcZOIYn0Xe9GsqKxJHrcNlK/XDCAVdqQ=="

if [ ! -f "$CSC" ]; then
    echo "PowerShell host for Steinberg's installer: .NET Framework 4.8 isn't in the prefix yet; skipping."
    exit 0
fi

STAMP="$( (cat "$SOURCE"; echo "$PUBLIC_KEY") | sha256sum | cut -d' ' -f1)"
if [ -f "$GAC_DIR/$NAME.dll" ] && [ "$(cat "$MARKER" 2>/dev/null)" = "$STAMP" ]; then
    echo "PowerShell host for Steinberg's installer is up to date."
    exit 0
fi
# Never replace a System.Management.Automation that isn't ours
if [ -f "$GAC_DIR/$NAME.dll" ] && ! grep -aq "$TAG" "$GAC_DIR/$NAME.dll"; then
    echo "The prefix has another $NAME; leaving it alone."
    exit 0
fi

echo "Building the PowerShell host for Steinberg's installer..."
BUILD_DIR="$TORQUIO_CACHE_DIR/powershell_host"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cp "$SOURCE" "$BUILD_DIR/"
echo "$PUBLIC_KEY" | base64 -d > "$BUILD_DIR/key.pub"
# The public key token is the last 8 bytes of the key's SHA-1, reversed
TOKEN="$(sha1sum "$BUILD_DIR/key.pub" | cut -c25-40 | fold -w2 | tac | tr -d '\n')"
if [ "$TOKEN" != "31bf3856ad364e35" ]; then
    echo "Error: the public key's token is $TOKEN, not 31bf3856ad364e35." >&2
    exit 1
fi

cd "$BUILD_DIR"
WINEDEBUG=-all wine 'C:\windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe' /nologo /noconfig /target:library \
    /optimize+ /warn:0 /delaysign+ /keyfile:key.pub /r:System.dll /out:"$NAME.dll" "$NAME.cs" </dev/null
if [ ! -s "$NAME.dll" ] || ! grep -aq "$TAG" "$NAME.dll"; then
    echo "Error: the PowerShell host couldn't be built." >&2
    exit 1
fi

mkdir -p "$GAC_DIR"
cp "$NAME.dll" "$GAC_DIR/$NAME.dll"
echo "$STAMP" > "$MARKER"
cd /
rm -rf -- "$BUILD_DIR"
echo "PowerShell host for Steinberg's installer installed."
