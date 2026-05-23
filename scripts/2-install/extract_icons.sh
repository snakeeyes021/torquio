#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
mkdir -p "$ICON_DIR"

extract_icon() {
    local primary_path="$1"
    local search_pattern="$2"
    local icon_name="$3"
    local extract_project="$4"
    local project_res_id="$5"
    local exe_path=""

    # 1. Try the hardcoded primary path
    if [ -f "$primary_path" ]; then
        exe_path="$primary_path"
    else
        echo "Warning: Hardcoded path not found for $icon_name."
        echo "Initiating fallback search using pattern: $search_pattern..."
        
        # 2. Fallback search in Program Files and Program Files (x86)
        # Using case-insensitive matching and catching common naming variations
        exe_path=$(find "$VALERIO_PREFIX_DIR/drive_c/Program Files" "$VALERIO_PREFIX_DIR/drive_c/Program Files (x86)" -type f -iname "$search_pattern" 2>/dev/null | head -n 1)
        
        if [ -z "$exe_path" ]; then
            echo "Error: Could not locate executable for $icon_name even with fallback search. Skipping."
            return
        fi
        echo "Found fallback executable at: $exe_path"
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
}

echo "Extracting Steinberg icons..."

# Dorico
# Variations: dorico.exe, dorico6.exe, Dorico 6.exe
extract_icon \
    "$VALERIO_PREFIX_DIR/drive_c/Program Files/Steinberg/Dorico6/Dorico6.exe" \
    "*dorico*.exe" \
    "valerio-dorico" \
    "true" \
    "1"

# SDA
# Variations: Steinberg Download Assistant.exe, SteinbergDownloadAssistant.exe, SDA.exe
extract_icon \
    "$VALERIO_PREFIX_DIR/drive_c/Program Files (x86)/Steinberg/Download Assistant/Steinberg Download Assistant.exe" \
    "*download*assistant*.exe" \
    "valerio-sda" \
    "false"

# SAM
# Variations: Steinberg Activation Manager.exe, SteinbergActivationManager.exe, SAM.exe
extract_icon \
    "$VALERIO_PREFIX_DIR/drive_c/Program Files/Steinberg/Activation Manager/SteinbergActivationManager.exe" \
    "*activation*manager*.exe" \
    "valerio-sam" \
    "false"

# Update icon cache
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor/" >/dev/null 2>&1 || true
fi

# Force the desktop environment to reload desktop entries to resolve the newly extracted icons
echo "Refreshing desktop database and application launchers..."
touch "$HOME/.local/share/applications" >/dev/null 2>&1 || true
if [ -d "$HOME/.local/share/applications" ]; then
    touch "$HOME/.local/share/applications/"*.desktop >/dev/null 2>&1 || true
fi

echo "Icon extraction complete."

