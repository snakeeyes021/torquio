#!/bin/bash
# Torquio Cleanup / Uninstaller Script
# This script wipes the Torquio environment including the container, data, and cache.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

wine="\033[38;5;125m"
gray="\033[38;5;244m"
green="\033[38;5;108m"
red="\033[38;5;167m"
yellow="\033[38;5;179m"
reset="\033[0m"

echo ""
echo -e "${red}### W A R N I N G ###${reset}"
echo ""
echo -e "⚠️  ${red}If you have not already deactivated your license(s), you will PERMANENTLY lose access!${reset}"
echo ""
echo -e "⚠️  ${red}If you store your Dorico projects inside the data directory (as opposed to somewhere in your user folder) and have not already backed them up, you will PERMANENTLY lose access!${reset}"
echo ""
echo ""
echo "This operation will permanently delete the following:"
echo -e " - Distrobox container: ${wine}$TORQUIO_CONTAINER_NAME${reset}"
echo -e " - Data directory:      ${gray}$TORQUIO_DATA_DIR${reset} (includes Wine prefix)"
echo -e " - Cache directory:     ${gray}$TORQUIO_CACHE_DIR${reset} (includes Wine source code and compilation artifacts)"
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

# Scaling Restore Prompt
ORIG_SCALE=$(get_config_val "original_scale_factor" "")
MANAGE_GRAPHICS=$(get_config_val "manage_graphics" "false")
if [ -n "$ORIG_SCALE" ] && ( [ "$MANAGE_GRAPHICS" = "true" ] || [ "$(get_config_val "auto_scale_mutter" "false")" = "true" ] ); then
    echo ""
    echo -e "Torquio detected that host display scaling was modified from ${wine}$ORIG_SCALE${reset} to ${wine}1.0${reset}."
    read -p "Would you like to restore your host display scale to $ORIG_SCALE? [Y/n]: " restore_confirm
    if [[ ! "$restore_confirm" =~ ^[Nn]$ ]]; then
        if command -v gsettings >/dev/null 2>&1; then
            gsettings set org.gnome.mutter xwayland-scaling-factor "$ORIG_SCALE" 2>/dev/null || true
            echo -e "  [${green}SUCCESS${reset}] Host display scale restored to $ORIG_SCALE."
        else
            echo -e "  [${yellow}WARNING${reset}] gsettings not found. Manual scale restore required."
        fi
    fi
fi

echo "Removing Distrobox container..."
distrobox rm "$TORQUIO_CONTAINER_NAME" --force || true

echo "Removing data and cache directories..."
rm -rf "$TORQUIO_DATA_DIR"
rm -rf "$TORQUIO_CACHE_DIR"
rm -rf "$HOME/.config/torquio"

echo "Removing host integrations..."
# Removing scripts from ~/.local/bin
rm -f "$HOME/.local/bin/torquio"
rm -f "$HOME/.local/bin/torquio-dorico"
rm -f "$HOME/.local/bin/torquio-sam"
rm -f "$HOME/.local/bin/torquio-sda-handler"

# Removing .desktop files
rm -f "$HOME/.local/share/applications/Dorico.desktop"
rm -f "$HOME/.local/share/applications/Steinberg Activation Manager.desktop"
rm -f "$HOME/.local/share/applications/steinberg-sda-handler.desktop"
rm -f "$HOME/.local/share/applications/wine-extension-dorico.desktop"

# Removing extracted icons
rm -f "$HOME/.local/share/icons/hicolor/256x256/apps/torquio-dorico.png"
rm -f "$HOME/.local/share/icons/hicolor/256x256/apps/torquio-dorico-project.png"
rm -f "$HOME/.local/share/icons/hicolor/256x256/apps/torquio-sda.png"
rm -f "$HOME/.local/share/icons/hicolor/256x256/apps/torquio-sam.png"

# Removing MIME types
rm -f "$HOME/.local/share/mime/packages/application-x-dorico.xml"

echo "Updating desktop database and icon cache..."
update-desktop-database "$HOME/.local/share/applications/" || true
update-mime-database "$HOME/.local/share/mime/" || true
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor/" || true
fi

echo -e "${green}Cleanup complete! The Torquio environment has been wiped.${reset}"
