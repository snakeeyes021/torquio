#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

REBUILD=false
if [ "$1" = "--rebuild" ] || [ "$1" = "-f" ] || [ "$1" = "--force" ]; then
    REBUILD=true
fi

if [ -f "/opt/wine-custom/.torquio_wine_build_complete" ] && [ "$REBUILD" = false ]; then
    echo "Custom Wine engine is already compiled and installed at /opt/wine-custom. Skipping build."
    exit 0
fi

echo "Adding i386 architecture..."
sudo dpkg --add-architecture i386

echo "Enabling source repos..."
sudo sed -i 's/^Types: deb$/Types: deb deb-src/' /etc/apt/sources.list.d/ubuntu.sources || true
sudo sed -i 's/^# deb-src/deb-src/' /etc/apt/sources.list || true

sudo apt update

echo "Attempting apt build-dep wine..."
sudo DEBIAN_FRONTEND=noninteractive apt-get build-dep -y wine || true

echo "Installing build dependencies..."
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
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
    sudo mkdir -p /usr/include/linux
    if [ -f "$SCRIPT_DIR/include/linux/ntsync.h" ]; then
        sudo cp "$SCRIPT_DIR/include/linux/ntsync.h" /usr/include/linux/ntsync.h
    elif [ -d /run/host/usr/src ]; then
        HOST_NTSYNC=$(find /run/host/usr/src -name ntsync.h 2>/dev/null | head -n 1)
        if [ -n "$HOST_NTSYNC" ]; then
            sudo cp "$HOST_NTSYNC" /usr/include/linux/ntsync.h
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
sudo mkdir -p /opt/wine-custom
sudo chown $USER:$USER /opt/wine-custom
cd ../wine64 && make install prefix=/opt/wine-custom
cd ../wine32 && make install prefix=/opt/wine-custom

touch /opt/wine-custom/.torquio_wine_build_complete
echo "Done building Wine!"