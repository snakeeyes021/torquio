# Valerio: Manual Deployment Playbook

This playbook documents the exact, step-by-step procedure required to manually achieve a working Steinberg environment on Linux using the "Valerio" architecture. 

It serves two purposes:
1. **For Users:** A guide for those who want to build the environment right now, before the automated `install.sh` wrapper is completed.
2. **For Developers:** The definitive blueprint that all future automation scripts must implement.

---

## ⚠️ A Note on Reproducibility & Versions

Steinberg software and Wine are both moving targets. To ensure a successful build, **it is recommend that you use the specific versions of software and commit hashes that have been validated together.**

Before starting, please consult **[docs/RELEASES.md](RELEASES.md)**. Throughout this playbook, we provide "Known-Good" examples based on the latest alpha release, but you should always check the manifest if you encounter issues.

---

## Phase 1: Host Preparation

1. **Install Distrobox and a Container Engine.**
   * Ensure `distrobox` and either `docker` or `podman` are installed on your host OS.
2. **Create the Environment.**
   * Create an Ubuntu 24.04 container. This ensures a stable, isolated environment for compiling the custom Wine build and running the apps.
   ```bash
   distrobox create -i ubuntu:24.04 -n steinberg-env
   ```
3. **Enter the Container.**
   * All subsequent commands in Phases 2, 3, and 4 must be run *inside* this container.
   ```bash
   distrobox enter steinberg-env
   ```

---

## Phase 2: Compiling the Custom Wine Engine

We must compile a custom branch of Wine that includes experimental `dcomp` stubs.

1. **Prepare the Build Environment:**
   ```bash
   sudo dpkg --add-architecture i386
   sudo sed -i 's/^Types: deb$/Types: deb deb-src/' /etc/apt/sources.list.d/ubuntu.sources || true
   sudo sed -i 's/^# deb-src/deb-src/' /etc/apt/sources.list || true
   sudo apt update
   sudo DEBIAN_FRONTEND=noninteractive apt-get build-dep -y wine || true
   ```
2. **Install Native Dependencies (CRITICAL: Includes ICU):**
   ```bash
   sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
       build-essential git flex bison pkg-config gcc-multilib g++-multilib mingw-w64 \
       libx11-dev:i386 libx11-dev libfreetype-dev:i386 libfreetype-dev \
       libdbus-1-dev:i386 libdbus-1-dev libfontconfig-dev:i386 libfontconfig-dev \
       libgnutls28-dev:i386 libgnutls28-dev libgl-dev:i386 libgl-dev \
       libunwind-dev:i386 libunwind-dev libxcomposite-dev:i386 libxcomposite-dev \
       libxcursor-dev:i386 libxcursor-dev libpulse-dev:i386 libpulse-dev \
       libasound2-dev:i386 libasound2-dev libvulkan-dev:i386 libvulkan-dev \
       libsdl2-dev:i386 libsdl2-dev libudev-dev:i386 libudev-dev \
       libicu-dev:i386 libicu-dev
   ```
3. **Clone the Custom Source & Checkout Validated Commit:**
   ```bash
   mkdir -p ~/dev/steinberg-on-linux/wine-build
   cd ~/dev/steinberg-on-linux/wine-build
   git clone https://gitlab.winehq.org/zhiyi/wine wine-source
   cd wine-source
   # Refer to RELEASES.md for the specific commit hash. 
   # Example (v0.1.1-alpha):
   git checkout ae88a705b5aa544cc60153d48c1ca8849f32ee14
   ```
4. **Compile and Install (Locally):**
   ```bash
   cd ..
   mkdir -p wine32 wine64

   # Build 64-bit
   cd wine64
   ../wine-source/configure --enable-win64
   make -j$(nproc)

   # Build 32-bit (Ensure it finds the 32-bit ICU via PKG_CONFIG_PATH)
   cd ../wine32
   PKG_CONFIG_PATH=/usr/lib/i386-linux-gnu/pkgconfig ../wine-source/configure --with-wine64=../wine64
   make -j$(nproc)

   # Install to /opt/wine-custom
   sudo mkdir -p /opt/wine-custom
   sudo chown $USER:$USER /opt/wine-custom
   cd ../wine64 && make install prefix=/opt/wine-custom
   cd ../wine32 && make install prefix=/opt/wine-custom
   ```

---

## Phase 3: Prefix Configuration

We must create an isolated Windows 10 environment for the Steinberg software.

1. **Set Environment Variables:**
   ```bash
   export WINEPREFIX="$HOME/dev/steinberg-on-linux/dorico-prefix"
   export WINE="/opt/wine-custom/bin/wine"
   export WINESERVER="/opt/wine-custom/bin/wineserver"
   export PATH="/opt/wine-custom/bin:$PATH"
   ```
2. **Initialize and Install Winetricks Dependencies:**
   ```bash
   wineboot -u
   # (Click through any popups that appear)
   
   # Download Winetricks (Ensure this matches the version in RELEASES.md)
   # Example (v0.1.1-alpha):
   wget https://raw.githubusercontent.com/Winetricks/winetricks/20260125-next/src/winetricks
   chmod +x winetricks
   
   ./winetricks -q d3dx9 msls31 allfonts d3dcompiler_43 d3dcompiler_47 vcrun2019 dotnet48 win10
   ```
3. **Manually Install Wine-ICU MSIs:**
   *(Do not let Wine try to automatically download these, it will fail. Ensure the version matches what is listed in RELEASES.md).*
   ```bash
   # Example (v0.1.1-alpha):
   wget https://dl.winehq.org/wine/wine-icu/72.1/wine-icu-72.1-x86.msi
   wget https://dl.winehq.org/wine/wine-icu/72.1/wine-icu-72.1-x86_64.msi
   wine msiexec /i wine-icu-72.1-x86.msi
   wine msiexec /i wine-icu-72.1-x86_64.msi
   ```

---

## Phase 4: Software Installation

You must provide your own Steinberg installer files. **Check RELEASES.md to ensure your installer versions match the environment's verified state.**

1. **Install MediaBay:**
   * Assuming you downloaded `MediaBay_Installer_win64.zip` to `~/dev/steinberg-on-linux`.
   ```bash
   cd ~/dev/steinberg-on-linux
   unzip -o MediaBay_Installer_win64.zip -d MediaBay_extracted
   # CRITICAL: Delete the preinstall script, it breaks the installer.
   # Note: The folder name inside the zip may change with versions.
   rm -f "MediaBay_extracted/MediaBay 1.3.60/Additional Content/Installer Data/preinstall.ps1"
   cd "MediaBay_extracted/MediaBay 1.3.60"
   wine Setup.exe
   ```
2. **Install Steinberg Download Assistant (SDA):**
   * Run the `.exe` you downloaded.
   ```bash
   cd ~/dev/steinberg-on-linux
   # Example version:
   wine Steinberg_Download_Assistant_1.39.3_Installer_win.exe
   ```
3. **Install NotePerformer (Optional):**
   * Run the `.exe` you downloaded.
   ```bash
   # Example version:
   wine NotePerformer_5.1.2_Installer.exe
   ```

---

## Phase 5: Host Integration (Outside Container)

To handle the web-browser login links (`net-steinberg-sam://`, etc.), you must link your host operating system to the scripts that execute Wine inside the container.

1. **Exit the container.**
   ```bash
   exit
   ```
2. **Install the `.desktop` Handlers:**
   * Copy the files from `desktop_stubs/` to your host's applications folder.
   ```bash
   cp ~/dev/steinberg-on-linux/desktop_stubs/*.desktop ~/.local/share/applications/
   ```
3. **Update the MIME Database:**
   * This tells your host browser to send the Steinberg links to the new `.desktop` handlers.
   ```bash
   update-desktop-database ~/.local/share/applications/
   ```
4. **Login:**
   * You can now launch Steinberg Download Assistant via its shell script wrapper (`scripts/3-runtime_handlers/sam.sh`), click "Login", and your host browser will successfully pass the login token back into the containerized Wine app.