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
    exit 10
fi
read -p "Have you backed up any Dorico projects you were keeping in the data directory? (y/N): " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 10
fi
read -p "If you have read the above warning and would like to proceed, type 'yes, permanently delete everything' to continue: " confirm

if [[ "$confirm" != "yes, permanently delete everything" ]]; then
    echo "Confirmation failed. Cleanup cancelled."
    exit 10
fi

# Scaling Restore Prompts
ORIG_SCALE=$(get_config_val "original_scale_factor" "")
ORIG_KDE=$(get_config_val "original_kde_policy" "")
ORIG_COSMIC=$(get_config_val "original_cosmic_policy" "")
MANAGE_GRAPHICS=$(get_config_val "manage_graphics" "false")

if [ "$MANAGE_GRAPHICS" = "true" ] || [ "$(get_config_val "auto_scale_mutter" "false")" = "true" ]; then
    # 1. GNOME Scaling Restore
    if [ -n "$ORIG_SCALE" ]; then
        echo ""
        echo -e "Torquio detected that host GNOME XWayland scaling was modified from ${wine}$ORIG_SCALE${reset} to ${wine}1${reset}."
        read -p "Would you like to restore your host display scale to $ORIG_SCALE? [Y/n]: " restore_confirm
        if [[ ! "$restore_confirm" =~ ^[Nn]$ ]]; then
            if command -v gsettings >/dev/null 2>&1; then
                if gsettings list-schemas | grep -q org.gnome.mutter.wayland; then
                    gsettings set org.gnome.mutter.wayland xwayland-scaling-factor "$ORIG_SCALE" 2>/dev/null || true
                else
                    gsettings set org.gnome.mutter xwayland-scaling-factor "$ORIG_SCALE" 2>/dev/null || true
                fi
                echo -e "  [${green}SUCCESS${reset}] Host display scale restored to $ORIG_SCALE."
            else
                echo -e "  [${yellow}WARNING${reset}] gsettings not found. Manual scale restore required."
            fi
        fi
    fi

    # 2. KDE Scaling Restore
    if [ -n "$ORIG_KDE" ]; then
        echo ""
        echo -e "Torquio detected that host KDE XWayland policy was modified from ${wine}$ORIG_KDE${reset} to ${wine}true${reset}."
        read -p "Would you like to restore your KDE XWayland clients scale policy to $ORIG_KDE? [Y/n]: " restore_confirm
        if [[ ! "$restore_confirm" =~ ^[Nn]$ ]]; then
            if command -v kwriteconfig6 >/dev/null 2>&1; then
                kwriteconfig6 --file kdeglobals --group KScreen --key XwaylandClientsScale "$ORIG_KDE" 2>/dev/null || true
                kwriteconfig6 --file kdeglobals --group KScreen --key XwaylandClientScale "$ORIG_KDE" 2>/dev/null || true
                dbus-send --session --dest=org.kde.KWin /KWin org.kde.KWin.reconfigure 2>/dev/null || true
                echo -e "  [${green}SUCCESS${reset}] Host KDE XWayland policy restored to $ORIG_KDE."
            else
                echo -e "  [${yellow}WARNING${reset}] kwriteconfig6 not found. Manual scale restore required."
            fi
        fi
    fi

    # 3. COSMIC Scaling Restore
    if [ -n "$ORIG_COSMIC" ]; then
        echo ""
        echo -e "Torquio detected that host COSMIC XWayland policy was modified from ${wine}$ORIG_COSMIC${reset} to ${wine}fractional${reset}."
        read -p "Would you like to restore your COSMIC XWayland clients scale policy to $ORIG_COSMIC? [Y/n]: " restore_confirm
        if [[ ! "$restore_confirm" =~ ^[Nn]$ ]]; then
            mkdir -p ~/.config/cosmic/com.system76.CosmicComp/v1
            if [ "$ORIG_COSMIC" = "none" ] || [ -z "$ORIG_COSMIC" ]; then
                rm -f ~/.config/cosmic/com.system76.CosmicComp/v1/descale_xwayland
            else
                echo "$ORIG_COSMIC" > ~/.config/cosmic/com.system76.CosmicComp/v1/descale_xwayland 2>/dev/null || true
            fi
            echo -e "  [${green}SUCCESS${reset}] Host COSMIC XWayland policy restored to $ORIG_COSMIC."
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
rm -f "$HOME/.local/bin/torquio_graphics.py"

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

echo "Removing orphaned Windows desktop shortcuts..."
host_desktop="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
if [ -f "$HOME/.config/user-dirs.dirs" ]; then
    host_desktop=$( (source "$HOME/.config/user-dirs.dirs" 2>/dev/null && echo "${XDG_DESKTOP_DIR:-$HOME/Desktop}") || echo "$host_desktop" )
fi
for dir in "$host_desktop" "$TORQUIO_PREFIX_DIR/drive_c/users/Public/Desktop" "$TORQUIO_PREFIX_DIR"/drive_c/users/*/Desktop; do
    if [ -d "$dir" ]; then
        find "$dir" -maxdepth 1 -type f \( \
            -name "Activation Manager.lnk" -o \
            -name "Steinberg Activation Manager.lnk" -o \
            -name "Dorico*.lnk" -o \
            -name "HALion*.lnk" -o \
            -name "Groove Agent*.lnk" -o \
            -name "Steinberg Library Manager.lnk" \
        \) -delete 2>/dev/null || true
    fi
done

echo "Updating desktop database and icon cache..."
update-desktop-database "$HOME/.local/share/applications/" || true
update-mime-database "$HOME/.local/share/mime/" || true
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor/" || true
fi

echo -e "${green}Cleanup complete! The Torquio environment has been wiped.${reset}"
