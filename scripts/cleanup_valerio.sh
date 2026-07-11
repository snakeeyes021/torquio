#!/bin/bash
# Valerio Cleanup / Uninstaller Script (Legacy)
# This script wipes the legacy Valerio environment including the container, data, and cache.

# Define legacy Valerio environment variables directly to remain self-contained
VALERIO_CONTAINER_NAME="valerio-env"
VALERIO_DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/valerio"
VALERIO_CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/valerio"

# Colors for user feedback
blue="\033[38;5;33m"
green="\033[38;5;108m"
red="\033[38;5;167m"
reset="\033[0m"

echo ""
echo -e "${red}### W A R N I N G (LEGACY VALERIO CLEANUP) ###${reset}"
echo ""
echo -e "⚠️  ${red}If you have not deactivated your license(s), you will PERMANENTLY lose access!${reset}"
echo -e "⚠️  ${red}If you store your Dorico projects inside the data directory, you will PERMANENTLY lose access!${reset}"
echo ""
echo "This operation will permanently delete the following legacy Valerio components:"
echo -e " - Distrobox container: ${blue}$VALERIO_CONTAINER_NAME${reset}"
echo -e " - Data directory:      ${blue}$VALERIO_DATA_DIR${reset} (includes Wine prefix)"
echo -e " - Cache directory:     ${blue}$VALERIO_CACHE_DIR${reset} (includes Wine source code and compilation artifacts)"
echo " - Host integration scripts and .desktop files"
echo " - Extracted desktop icons"
echo ""
read -p "Have you deactivated your license(s)? (y/N): " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 0
fi
read -p "Have you backed up any Dorico projects you were keeping in the data directory? (y/N): " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 0
fi
read -p "If you have read the above warning and would like to proceed, type 'yes, permanently delete everything' to continue: " confirm

if [[ "$confirm" != "yes, permanently delete everything" ]]; then
    echo "Confirmation failed. Cleanup cancelled."
    exit 0
fi

echo "Removing Distrobox container..."
distrobox rm "$VALERIO_CONTAINER_NAME" --force || true

echo "Removing data and cache directories..."
rm -rf "$VALERIO_DATA_DIR"
rm -rf "$VALERIO_CACHE_DIR"

echo "Removing host integrations..."
# Removing scripts from ~/.local/bin
rm -f "$HOME/.local/bin/dorico.sh"
rm -f "$HOME/.local/bin/sam.sh"
rm -f "$HOME/.local/bin/steinberg-sda-handler.sh"

# Removing .desktop files
rm -f "$HOME/.local/share/applications/Dorico.desktop"
rm -f "$HOME/.local/share/applications/Steinberg Activation Manager.desktop"
rm -f "$HOME/.local/share/applications/steinberg-sda-handler.desktop"
rm -f "$HOME/.local/share/applications/wine-extension-dorico.desktop"

# Removing extracted icons
rm -f "$HOME/.local/share/icons/hicolor/256x256/apps/valerio-dorico.png"
rm -f "$HOME/.local/share/icons/hicolor/256x256/apps/valerio-dorico-project.png"
rm -f "$HOME/.local/share/icons/hicolor/256x256/apps/valerio-sda.png"
rm -f "$HOME/.local/share/icons/hicolor/256x256/apps/valerio-sam.png"

# Removing MIME types
rm -f "$HOME/.local/share/mime/packages/application-x-dorico.xml"

echo "Updating desktop database and icon cache..."
update-desktop-database "$HOME/.local/share/applications/" || true
update-mime-database "$HOME/.local/share/mime/" || true
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor/" || true
fi

echo -e "${green}Cleanup complete! The legacy Valerio environment has been wiped.${reset}"
