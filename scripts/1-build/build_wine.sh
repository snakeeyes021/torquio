#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

if [ -f "/opt/wine-custom/.torquio_wine_build_complete" ]; then
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

echo "Cloning zhiyi wine branch..."
mkdir -p "$TORQUIO_BUILD_DIR"
cd "$TORQUIO_BUILD_DIR"

if [ ! -d "wine-source" ]; then
    git clone https://gitlab.winehq.org/zhiyi/wine wine-source
fi

cd wine-source
# Checkout the specific verified commit hash rather than the floating branch
# The below hash comes from the bug-23698-react-native-20251217 branch
git checkout ae88a705b5aa544cc60153d48c1ca8849f32ee14

echo "Configuring and building..."
cd ..
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