#!/bin/bash
# --- Logging Setup ---
TORQUIO_LOG_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/torquio/logs"
mkdir -p "$TORQUIO_LOG_DIR"
(ls -t "$TORQUIO_LOG_DIR"/*.log 2>/dev/null | tail -n +21 | xargs rm -f 2>/dev/null) &
LOG_FILE="$TORQUIO_LOG_DIR/torquio_cleanup_$(date +%Y-%m-%d_%H-%M-%S).log"
exec > >(tee -i "$LOG_FILE") 2>&1
echo "=== Torquio Cleanup Log Started: $(date) ==="
echo "Script: $0"
echo "========================================="

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
        cur_val=$(get_xwayland_scaling_factor)
        if [ "${cur_val:-0}" != "$ORIG_SCALE" ]; then
            from_desc=""
            if [ "$ORIG_SCALE" = "1" ]; then
                from_desc="Framebuffer Upscale (xwayland-scaling-factor=1)"
            elif [ "$ORIG_SCALE" = "0" ] || [ -z "$ORIG_SCALE" ]; then
                from_desc="System Default (xwayland-scaling-factor=0)"
            else
                from_desc="Override Scaling (xwayland-scaling-factor=$ORIG_SCALE)"
            fi
            
            to_desc=""
            if [ "$cur_val" = "1" ]; then
                to_desc="Framebuffer Upscale (xwayland-scaling-factor=1)"
            elif [ "$cur_val" = "0" ] || [ -z "$cur_val" ]; then
                to_desc="System Default (xwayland-scaling-factor=0)"
            else
                to_desc="Override Scaling (xwayland-scaling-factor=$cur_val)"
            fi

            echo ""
            echo -e "${blue}================================================================${reset}"
            echo -e "          ${wine}XWayland Global Scaling Policy Restore${reset}"
            echo -e "${blue}================================================================${reset}"
            echo -e "Torquio detected that host GNOME XWayland policy was modified from ${wine}$from_desc${reset} to ${wine}$to_desc${reset}."
            echo "During setup/launch, you set Torquio to automatically adjust your desktop"
            echo "environment's global XWayland scaling policy to match the ideal"
            echo "setting for Dorico."
            echo ""
            echo "Restoring this setting will return your system to its original scaling"
            echo "behavior (which may affect how other XWayland applications scale)."
            echo -e "${blue}================================================================${reset}"
            echo ""
            read -p "Would you like to restore your host display scale to $from_desc? [Y/n]: " restore_confirm
            if [[ ! "$restore_confirm" =~ ^[Nn]$ ]]; then
                if command -v gsettings >/dev/null 2>&1; then
                    if gsettings list-schemas | grep -q org.gnome.mutter.wayland; then
                        gsettings set org.gnome.mutter.wayland xwayland-scaling-factor "$ORIG_SCALE" 2>/dev/null || true
                    else
                        gsettings set org.gnome.mutter xwayland-scaling-factor "$ORIG_SCALE" 2>/dev/null || true
                    fi
                    echo -e "  [${green}SUCCESS${reset}] Host display scale restored to $from_desc."
                else
                    echo -e "  [${yellow}WARNING${reset}] gsettings not found. Manual scale restore required."
                fi
            fi
        fi
    fi

    # 2. KDE Scaling Restore
    if [ -n "$ORIG_KDE" ]; then
        kread_bin="kreadconfig6"
        command -v kreadconfig6 >/dev/null 2>&1 || kread_bin="kreadconfig5"
        cur_val=$($kread_bin --file kdeglobals --group KScreen --key XwaylandClientsScale 2>/dev/null)
        [ -z "$cur_val" ] && cur_val=$($kread_bin --file kdeglobals --group KScreen --key XwaylandClientScale 2>/dev/null)
        [ -z "$cur_val" ] && cur_val="true"
        if [ "$cur_val" != "$ORIG_KDE" ]; then
            from_desc=""
            if [ "$ORIG_KDE" = "false" ]; then
                from_desc="Scale XWayland clients by compositor (XwaylandClientsScale=false)"
            else
                from_desc="Scale XWayland clients themselves (XwaylandClientsScale=true)"
            fi
            
            to_desc=""
            if [ "$cur_val" = "false" ]; then
                to_desc="Scale XWayland clients by compositor (XwaylandClientsScale=false)"
            else
                to_desc="Scale XWayland clients themselves (XwaylandClientsScale=true)"
            fi

            echo ""
            echo -e "${blue}================================================================${reset}"
            echo -e "          ${wine}XWayland Global Scaling Policy Restore${reset}"
            echo -e "${blue}================================================================${reset}"
            echo "During setup/launch, Torquio automatically adjusted your desktop"
            echo "environment's global XWayland scaling policy to match the ideal"
            echo "setting for Dorico. This ensured Dorico's interface rendered crisply"
            echo "at high resolution (unscaled by the compositor) instead of looking blurry."
            echo ""
            echo "Restoring this setting will return your system to its original scaling"
            echo "behavior (which may affect how other XWayland applications scale)."
            echo -e "${blue}================================================================${reset}"
            echo ""
            echo -e "Torquio detected that host KDE XWayland policy was modified from ${wine}$from_desc${reset} to ${wine}$to_desc${reset}."
            read -p "Would you like to restore your KDE XWayland clients scale policy to $from_desc? [Y/n]: " restore_confirm
            if [[ ! "$restore_confirm" =~ ^[Nn]$ ]]; then
                kwrite_bin="kwriteconfig6"
                if ! command -v kwriteconfig6 >/dev/null 2>&1; then
                    if command -v kwriteconfig5 >/dev/null 2>&1; then
                        kwrite_bin="kwriteconfig5"
                    else
                        kwrite_bin=""
                    fi
                fi
                if [ -n "$kwrite_bin" ]; then
                    $kwrite_bin --file kdeglobals --group KScreen --key XwaylandClientsScale "$ORIG_KDE" 2>/dev/null || true
                    $kwrite_bin --file kdeglobals --group KScreen --key XwaylandClientScale "$ORIG_KDE" 2>/dev/null || true
                    dbus-send --session --dest=org.kde.KWin /KWin org.kde.KWin.reconfigure 2>/dev/null || true
                    echo -e "  [${green}SUCCESS${reset}] Host KDE XWayland policy restored to $from_desc."
                else
                    echo -e "  [${yellow}WARNING${reset}] kwriteconfig6 or kwriteconfig5 not found. Manual scale restore required."
                fi
            fi
        fi
    fi

    # 3. COSMIC Scaling Restore
    if [ -n "$ORIG_COSMIC" ]; then
        cur_val=$(cat ~/.config/cosmic/com.system76.CosmicComp/v1/descale_xwayland 2>/dev/null)
        [ -z "$cur_val" ] && cur_val="none"
        if [ "$cur_val" != "$ORIG_COSMIC" ]; then
            from_desc=""
            if [ "$ORIG_COSMIC" = "fractional" ]; then
                from_desc="Optimize for gaming and full-screen apps (descale_xwayland=fractional)"
            elif [ "$ORIG_COSMIC" = "true" ]; then
                from_desc="Optimize for applications (descale_xwayland=true)"
            else
                from_desc="Maximum compatibility mode (descale_xwayland=false)"
            fi
            
            to_desc=""
            if [ "$cur_val" = "fractional" ]; then
                to_desc="Optimize for gaming and full-screen apps (descale_xwayland=fractional)"
            elif [ "$cur_val" = "true" ]; then
                to_desc="Optimize for applications (descale_xwayland=true)"
            else
                to_desc="Maximum compatibility mode (descale_xwayland=false)"
            fi

            echo ""
            echo -e "${blue}================================================================${reset}"
            echo -e "          ${wine}XWayland Global Scaling Policy Restore${reset}"
            echo -e "${blue}================================================================${reset}"
            echo -e "Torquio detected that host COSMIC XWayland policy was modified from ${wine}$from_desc${reset} to ${wine}$to_desc${reset}."
            echo "During setup/launch, you set Torquio to automatically adjust your desktop"
            echo "environment's global XWayland scaling policy to match the ideal"
            echo "setting for Dorico."
            echo ""
            echo "Restoring this setting will return your system to its original scaling"
            echo "behavior (which may affect how other XWayland applications scale)."
            echo -e "${blue}================================================================${reset}"
            echo ""
            read -p "Would you like to restore your COSMIC XWayland clients scale policy to $from_desc? [Y/n]: " restore_confirm
            if [[ ! "$restore_confirm" =~ ^[Nn]$ ]]; then
                mkdir -p ~/.config/cosmic/com.system76.CosmicComp/v1
                if [ "$ORIG_COSMIC" = "none" ] || [ -z "$ORIG_COSMIC" ]; then
                    rm -f ~/.config/cosmic/com.system76.CosmicComp/v1/descale_xwayland
                else
                    echo "$ORIG_COSMIC" > ~/.config/cosmic/com.system76.CosmicComp/v1/descale_xwayland 2>/dev/null || true
                fi
                echo -e "  [${green}SUCCESS${reset}] Host COSMIC XWayland policy restored to $from_desc."
            fi
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
rm -f "$HOME/.local/share/applications/Steinberg Download Assistant.desktop"
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
