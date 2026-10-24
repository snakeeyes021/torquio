#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

# --rebuild: build even if an engine is installed. --deps-only / --skip-deps: only install the build
# dependencies / build without installing them (the container image build installs them in its own step).
REBUILD=false
DEPS=install
for arg in "$@"; do
    case "$arg" in
        --rebuild|-f|--force) REBUILD=true ;;
        --deps-only) DEPS=only ;;
        --skip-deps) DEPS=skip ;;
    esac
done

if [ -f "/opt/wine-custom/.torquio_wine_build_complete" ] && [ "$REBUILD" = false ] && [ "$DEPS" != only ]; then
    echo "Torquio's Wine engine is already installed in the container (/opt/wine-custom). Skipping build."
    exit 0
fi

# Root (the container image build) doesn't need sudo
SUDO=sudo
[ "$(id -u)" = 0 ] && SUDO=""

if [ "$DEPS" != skip ]; then

echo "Adding i386 architecture..."
$SUDO dpkg --add-architecture i386

echo "Enabling source repos..."
$SUDO sed -i 's/^Types: deb$/Types: deb deb-src/' /etc/apt/sources.list.d/ubuntu.sources || true
$SUDO sed -i 's/^# deb-src/deb-src/' /etc/apt/sources.list || true

$SUDO apt update

echo "Attempting apt build-dep wine..."
$SUDO env DEBIAN_FRONTEND=noninteractive apt-get build-dep -y wine || true

echo "Installing build dependencies..."
$SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential \
    git \
    flex \
    bison \
    pkg-config \
    gcc-multilib \
    g++-multilib \
    mingw-w64 \
    libx11-dev:i386 libx11-dev \
    libfreetype-dev:i386 libfreetype-dev \
    libdbus-1-dev:i386 libdbus-1-dev \
    libfontconfig-dev:i386 libfontconfig-dev \
    libgnutls28-dev:i386 libgnutls28-dev \
    libgl-dev:i386 libgl-dev \
    libunwind-dev:i386 libunwind-dev \
    libxcomposite-dev:i386 libxcomposite-dev \
    libxcursor-dev:i386 libxcursor-dev \
    libpulse-dev:i386 libpulse-dev \
    libasound2-dev:i386 libasound2-dev \
    libvulkan-dev:i386 libvulkan-dev \
    libsdl2-dev:i386 libsdl2-dev \
    libudev-dev:i386 libudev-dev \
    winetricks \
    unzip \
    cabextract \
    icoutils \
    libcups2 libcups2:i386 \
    x11-xserver-utils

fi
[ "$DEPS" = only ] && exit 0

echo "Cloning or updating zhiyi wine branch..."
mkdir -p "$TORQUIO_BUILD_DIR"
cd "$TORQUIO_BUILD_DIR"

if [ ! -d "wine-source" ]; then
    git clone https://gitlab.winehq.org/zhiyi/wine wine-source
fi

cd wine-source
# Fetch in case the repository was already cloned previously
git fetch origin

# Checkout the specific verified commit hash rather than the floating branch
# The below hash comes from the bug-23698-react-native branch (2026-03-24)
TARGET_COMMIT="883970826c62286c3da998072a5f49813d333a31"
git checkout -f "$TARGET_COMMIT"
git reset --hard "$TARGET_COMMIT"

PATCHES_DIR="$SCRIPT_DIR/patches"
if [ -d "$PATCHES_DIR" ]; then
    for patch_file in "$PATCHES_DIR"/*.patch; do
        if [ -f "$patch_file" ]; then
            echo "Applying $(basename "$patch_file")..."
            git apply "$patch_file"
        fi
    done
fi

# Re-enable /dev/ntsync in wineserver if disabled by upstream interim hack (e.g. c9bd766)
if [ -f server/inproc_sync.c ]; then
    sed -i '/get_inproc_device_fd/,/return -1/ s/#if 0/#if 1/' server/inproc_sync.c 2>/dev/null || true
fi

# Ensure linux/ntsync.h is present in the build environment so configure detects it
if [ ! -f /usr/include/linux/ntsync.h ]; then
    echo "Injecting ntsync.h header for Wine compilation..."
    $SUDO mkdir -p /usr/include/linux
    if [ -f "$SCRIPT_DIR/include/linux/ntsync.h" ]; then
        $SUDO cp "$SCRIPT_DIR/include/linux/ntsync.h" /usr/include/linux/ntsync.h
    elif [ -d /run/host/usr/src ]; then
        HOST_NTSYNC=$(find /run/host/usr/src -name ntsync.h 2>/dev/null | head -n 1)
        if [ -n "$HOST_NTSYNC" ]; then
            $SUDO cp "$HOST_NTSYNC" /usr/include/linux/ntsync.h
        fi
    fi
fi

echo "Configuring and building..."
cd ..

if [ "$REBUILD" = true ]; then
    echo "Cleaning previous build directories..."
    rm -rf wine32 wine64
fi

mkdir -p wine32 wine64

cd wine64
../wine-source/configure --enable-win64
make -j$(nproc)

cd ../wine32
PKG_CONFIG_PATH=/usr/lib/i386-linux-gnu/pkgconfig ../wine-source/configure --with-wine64=../wine64
make -j$(nproc)

echo "Installing locally to /opt/wine-custom..."
$SUDO mkdir -p /opt/wine-custom
# -R: an engine from the prebuilt image is owned by root
[ -n "$SUDO" ] && sudo chown -R "$USER:$USER" /opt/wine-custom
cd ../wine64 && make install prefix=/opt/wine-custom
cd ../wine32 && make install prefix=/opt/wine-custom

# Record what this engine was built from, for `torquio --manifest`
mkdir -p /opt/wine-custom/share/torquio
{
    echo "zhiyi_commit=$TARGET_COMMIT"
    echo "torquio_commit=${TORQUIO_COMMIT:-$(git -C "$SCRIPT_DIR" describe --always --dirty --tags 2>/dev/null)}"
    echo "built=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    for patch_file in "$PATCHES_DIR"/*.patch; do
        if [ -f "$patch_file" ]; then
            echo "patch=$(sha256sum "$patch_file" | cut -c1-12) $(basename "$patch_file" .patch)"
        fi
    done
} > /opt/wine-custom/share/torquio/build-info

touch /opt/wine-custom/.torquio_wine_build_complete
echo "Done building Wine!"