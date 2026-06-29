#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

INITIAL_INSTALL=false
if [[ "$1" == "--initial" ]]; then
    INITIAL_INSTALL=true
fi

# Ensure directories exist
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
mkdir -p "$ICON_DIR"
mkdir -p "$HOME/.local/share/applications"

update_host_icon_cache() {
    if command -v distrobox-host-exec >/dev/null 2>&1; then
        distrobox-host-exec gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor/" >/dev/null 2>&1 || true
        distrobox-host-exec touch "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
    elif command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor/" >/dev/null 2>&1 || true
        touch "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
    fi
}

extract_icon() {
    local primary_path="$1"
    local search_pattern="$2"
    local icon_name="$3"
    local extract_project="$4"
    local project_res_id="$5"
    local desktop_name="$6"
    local exe_path=""

    # 1. Try the hardcoded primary path
    if [ -f "$primary_path" ]; then
        exe_path="$primary_path"
    else
        if [ "$INITIAL_INSTALL" = "false" ]; then
            echo "Warning: Hardcoded path not found for $icon_name."
            echo "Initiating fallback search using pattern: $search_pattern..."
        fi
        
        # 2. Fallback search in Program Files and Program Files (x86)
        # Using case-insensitive matching and catching common naming variations
        exe_path=$(find "$TORQUIO_PREFIX_DIR/drive_c/Program Files" "$TORQUIO_PREFIX_DIR/drive_c/Program Files (x86)" -type f -iname "$search_pattern" 2>/dev/null | head -n 1)
        
        if [ -z "$exe_path" ]; then
            if [ "$INITIAL_INSTALL" = "true" ]; then
                echo "Info: $icon_name is not yet installed in the Wine prefix. The launcher and icon will be automatically registered when installed via the Download Assistant."
            else
                echo "Error: Could not locate executable for $icon_name even with fallback search. Skipping."
            fi
            return
        fi
        
        if [ "$INITIAL_INSTALL" = "false" ]; then
            echo "Found fallback executable at: $exe_path"
        fi
    fi
    
    echo "Extracting icon from $exe_path to $icon_name..."
    local tmp_dir=$(mktemp -d)
    
    # Extract all icon resources (group 14)
    wrestool -x -t 14 "$exe_path" -o "$tmp_dir/" 2>/dev/null || true
    
    # Check if anything was extracted
    local ico_file=$(ls "$tmp_dir"/*.ico 2>/dev/null | head -n 1)
    
    if [ -n "$ico_file" ]; then
        # Extract all sizes from the .ico to PNGs
        icotool -x "$ico_file" -o "$tmp_dir/" 2>/dev/null || true
        
        # Find the largest PNG (usually 256x256, sort by file size descending)
        local best_png=$(ls -S "$tmp_dir"/*.png 2>/dev/null | head -n 1)
        
        if [ -n "$best_png" ]; then
            cp "$best_png" "$ICON_DIR/${icon_name}.png"
            echo "Successfully installed ${icon_name}.png"
        else
            echo "No PNG could be extracted from $ico_file"
        fi
    else
        echo "No ICO resource found in $exe_path"
    fi
    
    # --- Precision Project Icon Extraction ---
    if [ "$extract_project" == "true" ] && [ -n "$project_res_id" ]; then
        echo "Extracting project icon (ID: $project_res_id) from $exe_path to ${icon_name}-project..."
        local proj_tmp=$(mktemp -d)
        
        # Extract ONLY the specific resource ID
        wrestool -x -t 14 -n "$project_res_id" "$exe_path" -o "$proj_tmp/" 2>/dev/null || true
        
        local proj_ico=$(ls "$proj_tmp"/*.ico 2>/dev/null | head -n 1)
        
        if [ -n "$proj_ico" ]; then
            icotool -x "$proj_ico" -o "$proj_tmp/" 2>/dev/null || true
            local best_proj_png=$(ls -S "$proj_tmp"/*.png 2>/dev/null | head -n 1)
            
            if [ -n "$best_proj_png" ]; then
                cp "$best_proj_png" "$ICON_DIR/${icon_name}-project.png"
                echo "Successfully installed ${icon_name}-project.png"
            else
                echo "No PNG could be extracted from $proj_ico"
            fi
        else
            echo "No ICO resource found for ID $project_res_id in $exe_path"
        fi
        rm -rf "$proj_tmp"
    fi
    # ----------------------------------------------
    
    rm -rf "$tmp_dir"
    
    # --- Update Host Icon Cache BEFORE Desktop Launcher Registration ---
    update_host_icon_cache
    
    # --- Dynamic Desktop Launcher Registration ---
    if [ -n "$desktop_name" ] && [ -f "$SCRIPT_DIR/../../desktop_stubs/$desktop_name" ]; then
        echo "Registering desktop launcher: $desktop_name..."
        sed "s|\$HOME|$HOME|g" "$SCRIPT_DIR/../../desktop_stubs/$desktop_name" > "$HOME/.local/share/applications/$desktop_name"
        
        # Update desktop database for the new launcher
        if command -v distrobox-host-exec >/dev/null 2>&1; then
            distrobox-host-exec update-desktop-database "$HOME/.local/share/applications/" >/dev/null 2>&1 || true
        elif command -v update-desktop-database >/dev/null 2>&1; then
            update-desktop-database "$HOME/.local/share/applications/" >/dev/null 2>&1 || true
        fi
    fi
}

echo "Extracting Torquio icons and registering launchers..."

# Dorico
# Variations: dorico.exe, dorico6.exe, Dorico 6.exe
extract_icon \
    "$TORQUIO_PREFIX_DIR/drive_c/Program Files/Steinberg/Dorico6/Dorico6.exe" \
    "*dorico*.exe" \
    "torquio-dorico" \
    "true" \
    "1" \
    "Dorico.desktop"

# SDA
# Variations: Steinberg Download Assistant.exe, SteinbergDownloadAssistant.exe, SDA.exe
extract_icon \
    "$TORQUIO_PREFIX_DIR/drive_c/Program Files (x86)/Steinberg/Download Assistant/Steinberg Download Assistant.exe" \
    "*download*assistant*.exe" \
    "torquio-sda" \
    "false" \
    "" \
    "Steinberg Download Assistant.desktop"

# SAM
# Variations: Steinberg Activation Manager.exe, SteinbergActivationManager.exe, SAM.exe
extract_icon \
    "$TORQUIO_PREFIX_DIR/drive_c/Program Files/Steinberg/Activation Manager/SteinbergActivationManager.exe" \
    "*activation*manager*.exe" \
    "torquio-sam" \
    "false" \
    "" \
    "Steinberg Activation Manager.desktop"

# Update icon cache
if command -v distrobox-host-exec >/dev/null 2>&1; then
    distrobox-host-exec gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor/" >/dev/null 2>&1 || true
elif command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor/" >/dev/null 2>&1 || true
fi

# Force the desktop environment to reload desktop entries to resolve the newly extracted icons
echo "Refreshing desktop database and application launchers..."
if command -v distrobox-host-exec >/dev/null 2>&1; then
    distrobox-host-exec update-desktop-database "$HOME/.local/share/applications/" >/dev/null 2>&1 || true
elif command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications/" >/dev/null 2>&1 || true
fi
touch "$HOME/.local/share/applications" >/dev/null 2>&1 || true
if [ -d "$HOME/.local/share/applications" ]; then
    touch "$HOME/.local/share/applications/"*.desktop >/dev/null 2>&1 || true
fi

echo "Icon extraction complete."
