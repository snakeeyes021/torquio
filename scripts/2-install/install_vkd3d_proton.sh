#!/bin/bash
# Fetch vkd3d-proton, a Direct3D 12 implementation on Vulkan, for AI plug-ins that run their models on the
# GPU through DirectML (e.g. Cantai). Wine's builtin d3d12 computes DirectML wrong, so these plug-ins only
# get the GPU when they use vkd3d-proton; the Dorico launcher copies the DLLs next to each such plug-in's
# executable and sets a per-app DLL override, leaving every other program on Wine's builtin d3d12.
# The DLLs are kept in $TORQUIO_DATA_DIR/vkd3d-proton/<version>/.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

VKD3D_PROTON_VERSION="3.0.1"
VKD3D_PROTON_SHA256="3cf2315522af5e43605ef6d3c41dad91387040bf97199934f3f7ab76caaa2f0c"
VKD3D_PROTON_URL="https://github.com/HansKristian-Work/vkd3d-proton/releases/download/v$VKD3D_PROTON_VERSION/vkd3d-proton-$VKD3D_PROTON_VERSION.tar.zst"
ARCHIVE="$TORQUIO_CACHE_DIR/vkd3d-proton/vkd3d-proton-$VKD3D_PROTON_VERSION.tar.zst"
DEST="$TORQUIO_DATA_DIR/vkd3d-proton/$VKD3D_PROTON_VERSION"

if [ -f "$DEST/d3d12.dll" ] && [ -f "$DEST/d3d12core.dll" ]; then
    echo "vkd3d-proton $VKD3D_PROTON_VERSION already provisioned."
    exit 0
fi

mkdir -p "$(dirname "$ARCHIVE")"
if [ ! -f "$ARCHIVE" ] || ! echo "$VKD3D_PROTON_SHA256  $ARCHIVE" | sha256sum -c --status; then
    echo "Downloading vkd3d-proton $VKD3D_PROTON_VERSION (~5 MB)..."
    curl -fL --progress-bar -o "$ARCHIVE.part" "$VKD3D_PROTON_URL"
    if ! echo "$VKD3D_PROTON_SHA256  $ARCHIVE.part" | sha256sum -c --status; then
        rm -f "$ARCHIVE.part"
        echo "Error: the vkd3d-proton download doesn't match its expected checksum."
        exit 1
    fi
    mv "$ARCHIVE.part" "$ARCHIVE"
fi

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT
EXTRACT="tar --zstd -xf \"$ARCHIVE\" -C \"$TMP_DIR\" \"vkd3d-proton-$VKD3D_PROTON_VERSION/x64\""
if command -v zstd >/dev/null 2>&1; then
    bash -c "$EXTRACT"
else
    distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "command -v zstd >/dev/null || sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq zstd >/dev/null; $EXTRACT"
fi
mkdir -p "$DEST"
cp "$TMP_DIR/vkd3d-proton-$VKD3D_PROTON_VERSION/x64/d3d12.dll" "$TMP_DIR/vkd3d-proton-$VKD3D_PROTON_VERSION/x64/d3d12core.dll" "$DEST/"
echo "vkd3d-proton $VKD3D_PROTON_VERSION provisioned in $DEST."
