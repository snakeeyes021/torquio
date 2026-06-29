#!/bin/bash
set -e

# --- Logging Setup ---
TORQUIO_LOG_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/torquio/logs"
mkdir -p "$TORQUIO_LOG_DIR"
(ls -t "$TORQUIO_LOG_DIR"/*.log 2>/dev/null | tail -n +21 | xargs rm -f 2>/dev/null) &
LOG_FILE="$TORQUIO_LOG_DIR/torquio_install_$(date +%Y-%m-%d_%H-%M-%S).log"
exec > >(tee -i "$LOG_FILE") 2>&1
echo "=== Torquio Install Log Started: $(date) ==="
echo "Script: $0"
echo "========================================="

# Torquio Master Installer
# This script automates the installation and configuration wizard process for Steinberg software on Linux.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$SCRIPT_DIR/scripts/common.sh"

AUTO_ACCEPT=false
if [[ "$1" == "-y" ]] || [[ "$1" == "--yes" ]]; then
    AUTO_ACCEPT=true
fi

wine="\033[38;5;125m"
gray="\033[38;5;244m"
green="\033[38;5;108m"
red="\033[38;5;167m"
yellow="\033[38;5;179m"
blue="\033[38;5;110m"
dark_gray="\033[38;5;240m"
reset="\033[0m"

print_wizard_banner() {
    clear 2>/dev/null || true
    echo -e "${gray}================================================================${reset}"
    echo -e " ${wine} ████████╗  ██████╗  ██████╗   ██████╗  ██╗   ██╗ ██╗  ██████╗${reset}"
    echo -e " ${wine} ╚══██╔══╝ ██╔═══██╗ ██╔══██╗ ██╔═══██╗ ██║   ██║ ██║ ██╔═══██╗${reset}"
    echo -e " ${wine}    ██║    ██║   ██║ ██████╔╝ ██║   ██║ ██║   ██║ ██║ ██║   ██║${reset}"
    echo -e " ${wine}    ██║    ██║   ██║ ██╔══██╗ ██║▄▄ ██║ ██║   ██║ ██║ ██║   ██║${reset}"
    echo -e " ${wine}    ██║    ╚██████╔╝ ██║  ██║ ╚██████╔╝ ╚██████╔╝ ██║ ╚██████╔╝${reset}"
    echo -e " ${wine}    ╚═╝     ╚═════╝  ╚═╝  ╚═╝  ╚══▀▀═╝   ╚═════╝  ╚═╝  ╚═════╝${reset}"
    echo -e " ${wine}                            —— B Y  R E D  F O X  L A B S ——${reset}"
    echo -e "${gray}================================================================${reset}"
    echo -e "                    TORQUIO INSTALLATION WIZARD                 "
    echo -e "${gray}================================================================${reset}"
    echo ""
}

clean_desktop_lnk() {
    local host_desktop="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
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
}

# 1. State Detection & Action Choice
CONTAINER_EXISTS=false
if distrobox list 2>/dev/null | grep -q "$TORQUIO_CONTAINER_NAME"; then
    CONTAINER_EXISTS=true
fi

PREFIX_EXISTS=false
if [ -d "$TORQUIO_PREFIX_DIR" ]; then
    PREFIX_EXISTS=true
fi

CORE_INSTALLED=false
if [ -f "$TORQUIO_PREFIX_DIR/.torquio_core_installed" ]; then
    CORE_INSTALLED=true
fi

PARTIAL_INSTALL=false
if { [ "$CONTAINER_EXISTS" = true ] || [ "$PREFIX_EXISTS" = true ]; } && [ "$CORE_INSTALLED" = false ]; then
    PARTIAL_INSTALL=true
fi

ACTION="install"
RUN_WIZARD=true

if [ "$AUTO_ACCEPT" = false ] && { [ "$CONTAINER_EXISTS" = true ] || [ "$PREFIX_EXISTS" = true ]; }; then
    print_wizard_banner
    
    c_status="${red}Missing${reset}"
    if [ "$CONTAINER_EXISTS" = true ]; then
        c_status="${green}Created${reset}"
    fi
    p_status="${red}Missing${reset}"
    if [ "$PREFIX_EXISTS" = true ]; then
        p_status="${green}Initialized${reset}"
    fi
    d_status="${red}Incomplete${reset}"
    if [ "$CORE_INSTALLED" = true ]; then
        d_status="${green}Installed${reset}"
    fi
    
    echo -e "${blue}Existing Torquio Environment Detected:${reset}"
    echo -e "  - Distrobox Container:      $c_status"
    echo -e "  - Wine Prefix:              $p_status"
    echo -e "  - Core Wine Dependencies:   $d_status"
    echo ""
    
    if [ "$PARTIAL_INSTALL" = true ]; then
        echo -e "${yellow}⚠️  PARTIAL INSTALLATION DETECTED:${reset}"
        echo "  Some setup steps did not complete successfully during the previous run."
        echo "  It is completely safe to resume; Torquio will skip already completed"
        echo "  phases (like container creation or Wine compilation) and resume building"
        echo "  the missing pieces."
        echo ""
        echo "How would you like to proceed?"
        echo -e "  ${wine}1)${reset} Resume / Repair Incomplete Installation"
        echo -e "  ${wine}2)${reset} Fresh Reinstallation (Deletes container & Wine prefix)"
        echo -e "  ${wine}3)${reset} Cancel and Exit"
        echo ""
        
        read -p "Select an option (1-3): " choice_action
        case "$choice_action" in
            1)
                ACTION="resume"
                ;;
            2)
                if "$SCRIPT_DIR/scripts/cleanup.sh"; then
                    ACTION="install"
                else
                    rc=$?
                    if [ $rc -eq 10 ]; then
                        exit 10
                    else
                        exit $rc
                    fi
                fi
                ;;
            3)
                echo -e "${red}Installation cancelled.${reset}"
                exit 10
                ;;
            *)
                echo "Invalid selection. Installation cancelled."
                exit 10
                ;;
        esac
    else
        echo "An existing installation was detected. How would you like to proceed?"
        echo -e "  ${wine}1)${reset} Configure Settings Only (No container or Wine rebuilding)"
        echo -e "  ${wine}2)${reset} Re-run Windows Software Installers (MediaBay, SDA, NotePerformer)"
        echo -e "  ${wine}3)${reset} Recreate Distrobox Container Only (Preserves Wine prefix & licenses)"
        echo -e "  ${wine}4)${reset} Fresh Reinstallation (Deletes container & Wine prefix)"
        echo -e "  ${wine}5)${reset} Cancel and Exit"
        echo ""
        
        read -p "Select an option (1-5): " choice_action
        case "$choice_action" in
            1)
                ACTION="config_only"
                ;;
            2)
                ACTION="reinstall_software"
                ;;
            3)
                ACTION="recreate_container"
                ;;
            4)
                if "$SCRIPT_DIR/scripts/cleanup.sh"; then
                    ACTION="install"
                else
                    rc=$?
                    if [ $rc -eq 10 ]; then
                        exit 10
                    else
                        exit $rc
                    fi
                fi
                ;;
            5)
                echo -e "${red}Installation cancelled.${reset}"
                exit 10
                ;;
            *)
                echo "Invalid selection. Installation cancelled."
                exit 10
                ;;
        esac
    fi
fi

# Define active phases based on selected action
CREATE_CONTAINER=true
BUILD_WINE=true
SETUP_PREFIX=true
INSTALL_SOFTWARE=true
INTEGRATE=true

if [ "$ACTION" = "config_only" ]; then
    CREATE_CONTAINER=false
    BUILD_WINE=false
    SETUP_PREFIX=false
    INSTALL_SOFTWARE=false
elif [ "$ACTION" = "reinstall_software" ]; then
    CREATE_CONTAINER=true
    BUILD_WINE=true
    SETUP_PREFIX=true
    INSTALL_SOFTWARE=true
elif [ "$ACTION" = "recreate_container" ]; then
    CREATE_CONTAINER=true
    BUILD_WINE=true
    SETUP_PREFIX=false
    INSTALL_SOFTWARE=false
    # Remove existing container to force recreation
    distrobox rm "$TORQUIO_CONTAINER_NAME" --force || true
elif [ "$ACTION" = "resume" ]; then
    CREATE_CONTAINER=true
    BUILD_WINE=true
    SETUP_PREFIX=true
    INSTALL_SOFTWARE=true
fi

# Prerequisite Checks
if [ "$CREATE_CONTAINER" = true ]; then
    echo "Checking prerequisites..."
    if ! command -v distrobox >/dev/null 2>&1; then
        echo -e "${red}Error: distrobox is not installed.${reset}"
        echo "Please install distrobox and either docker or podman."
        exit 1
    fi
    if ! command -v docker >/dev/null 2>&1 && ! command -v podman >/dev/null 2>&1; then
        echo -e "${red}Error: Neither docker nor podman was found.${reset}"
        echo "Please install one of them to use with distrobox."
        exit 1
    fi
fi

# 2. Interactive Settings Wizard
CUR_MANAGE=$(get_config_val "manage_graphics" "false")
CUR_MANUAL_DPI=$(get_config_val "manual_dpi" "96")
CUR_MATCH_PHYS=$(get_config_val "match_physical_dpi" "false")
CUR_FREETYPE=$(get_config_val "freetype_interpreter" "40")

SET_MANAGE="$CUR_MANAGE"
SET_MANUAL_DPI="$CUR_MANUAL_DPI"
SET_MATCH_PHYS="$CUR_MATCH_PHYS"
SET_FREETYPE="$CUR_FREETYPE"
MAPPED_FOLDER_PATH=""
MAPPED_FOLDER_TYPE="drive"
IMPORT_SHORTCUTS_PATH=""

if [ "$AUTO_ACCEPT" = false ]; then
    # Step 1: Graphics & Display scaling
    print_wizard_banner
    echo -e "${blue}[Step 1 of 4] Display Scaling & Graphics Management${reset}"
    echo "--------------------------------------------------"
    echo -e "${gray}Note: You can change all configuration settings later at any time${reset}"
    echo -e "${gray}by re-running the configuration wizard or via the Torquio menus.${reset}"
    echo "--------------------------------------------------"
    if [ "$XDG_SESSION_TYPE" = "x11" ]; then
        echo "X11 session detected."
        echo ""
        echo "Automated scaling management is a Wayland-only feature."
        echo "Proper scaling settings will differ for various X11 desktop environments."
        echo "If needed, you can adjust your WINE Prefix DPI manually via Torquio."
        echo ""
        SET_MANAGE="false"
        SET_MATCH_PHYS="false"
        SET_MANUAL_DPI="$CUR_MANUAL_DPI"
        read -p "Press [Enter] to continue to the next step..." temp
    else
        echo "Torquio can automatically coordinate your Wayland desktop's XWayland"
        echo "scaling policy and Wine DPI settings for optimal rendering."
        echo ""

        def_manage="Y"
        if [ "$CUR_MANAGE" = "false" ]; then def_manage="N"; fi
        manage_bracket="[Y/n]"
        if [ "$def_manage" = "N" ]; then manage_bracket="[y/N]"; fi

        read -p "Would you like Torquio to automatically manage display scaling? $manage_bracket: " auto_scaling

        if [[ -z "$auto_scaling" && "$def_manage" = "Y" ]] || [[ "$auto_scaling" =~ ^[Yy]$ ]]; then
            SET_MANAGE="true"
            SET_MANUAL_DPI="96"
            SET_MATCH_PHYS="$CUR_MATCH_PHYS"
        else
            SET_MANAGE="false"
            SET_MATCH_PHYS="false"
            SET_MANUAL_DPI="96"
            echo ""
            echo -e "${gray}Manual Mode selected. Defaulting to standard 96 DPI.${reset}"
            echo -e "${gray}You can customize your scaling policy and DPI settings later via the Torquio configuration menu.${reset}"
            echo ""
        fi
    fi

    # Step 2: Font Hinting Style
    print_wizard_banner
    echo -e "${blue}[Step 2 of 4] FreeType Font Hinting Interpreter${reset}"
    echo "--------------------------------------------------"
    echo "Select your preferred font smoothing style:"
    echo "  1) v40 (Thicker/bolder, but some fonts can look smudgey) [Default]"
    echo "  2) v35 (Thinner/crisper, but some fonts can look anemic)"
    echo ""
    read -p "Selection (1-2) [Current: v$CUR_FREETYPE]: " choice_ft
    case "$choice_ft" in
        1)
            SET_FREETYPE="40"
            ;;
        2)
            SET_FREETYPE="35"
            ;;
        *)
            SET_FREETYPE="$CUR_FREETYPE"
            ;;
    esac
    
    # Step 3: Project Folder Mapping
    print_wizard_banner
    echo -e "${blue}[Step 3 of 4] User Project Folder Mapping${reset}"
    echo "--------------------------------------------------"
    echo "You can map a directory on your host machine (like your music or project folder) so that it"
    echo "appears as a network drive (e.g., D:\\, E:\\) or in the desktop shortcuts inside the Wine prefix."
    echo ""
    read -p "Would you like to map a local folder to WINE? [Y/n]: " map_confirm
    if [[ -z "$map_confirm" ]] || [[ "$map_confirm" =~ ^[Yy]$ ]]; then
        map_path=""
        if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
            if command -v zenity >/dev/null 2>&1; then
                map_path=$(zenity --file-selection --directory --title="Select Folder to Map" 2>/dev/null) || true
            elif command -v kdialog >/dev/null 2>&1; then
                map_path=$(kdialog --getexistingdirectory --title="Select Folder to Map" 2>/dev/null) || true
            fi
        fi
        if [ -z "$map_path" ]; then
            read -p "Enter the absolute path of the local folder: " map_path
        fi
        
        if [ -d "$map_path" ]; then
            MAPPED_FOLDER_PATH="$map_path"
            echo -e "  [${green}SUCCESS${reset}] Folder path is valid."
            echo ""
            echo "Select how you would like to map this folder in Wine:"
            echo -e "  ${wine}1)${reset} As a Mapped Network Drive (e.g., D:\\, E:\\) [Default]"
            echo -e "  ${wine}2)${reset} As a Shortcut inside your Desktop folder (auto-expanded in file pickers)"
            echo ""
            read -p "Select choice (1-2): " choice_type
            if [ "$choice_type" = "2" ]; then
                MAPPED_FOLDER_TYPE="desktop"
                echo "Will map as a Desktop shortcut during integration."
            else
                MAPPED_FOLDER_TYPE="drive"
                echo "Will map as a network drive during integration."
            fi
        else
            echo -e "  [${red}ERROR${reset}] Path does not exist or is not a folder. Skipping mapping."
        fi
        sleep 2
    fi
    
    # Step 4: Keyboard Shortcuts Import
    print_wizard_banner
    echo -e "${blue}[Step 4 of 4] Keyboard Shortcuts Import${reset}"
    echo "--------------------------------------------------"
    echo "If you have a backup of your custom Dorico keyboard shortcuts (.zip or .json),"
    echo "Torquio can automatically import them for you."
    echo ""
    FOUND_BACKUP=$(find "$HOME/Downloads" -maxdepth 1 -type f \( -name "torquio_keycommands_backup.zip" -o -name "keycommands_*.json" \) 2>/dev/null | head -n 1)
    if [ -n "$FOUND_BACKUP" ]; then
        echo -e "Detected shortcut backup at: ${wine}$(basename "$FOUND_BACKUP")${reset}"
        read -p "Import this backup file? [Y/n]: " import_def
        if [[ ! "$import_def" =~ ^[Nn]$ ]]; then
            IMPORT_SHORTCUTS_PATH="$FOUND_BACKUP"
        else
            # User rejected the auto-detected one, so ask if they want to browse for another one
            read -p "Import custom keyboard shortcuts? [y/N]: " import_confirm
            if [[ "$import_confirm" =~ ^[Yy]$ ]]; then
                import_path=""
                if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
                    if command -v zenity >/dev/null 2>&1; then
                        import_path=$(zenity --file-selection --file-filter="Backup (*.zip *.json) | *.zip *.json" --title="Select Key Commands Backup File" 2>/dev/null) || true
                    elif command -v kdialog >/dev/null 2>&1; then
                        import_path=$(kdialog --getopenfilename "$HOME/Downloads" "*.zip *.json" --title="Select Key Commands Backup File" 2>/dev/null) || true
                    fi
                fi
                if [ -z "$import_path" ]; then
                    read -p "Enter the path to your shortcut backup (.zip or .json): " import_path
                fi
                
                if [ -f "$import_path" ]; then
                    IMPORT_SHORTCUTS_PATH="$import_path"
                    echo -e "  [${green}SUCCESS${reset}] File found. Will import during integration."
                else
                    echo -e "  [${red}ERROR${reset}] File does not exist. Skipping import."
                fi
                sleep 2
            fi
        fi
    else
        read -p "Import custom keyboard shortcuts? [y/N]: " import_confirm
        if [[ "$import_confirm" =~ ^[Yy]$ ]]; then
            import_path=""
            if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
                if command -v zenity >/dev/null 2>&1; then
                    import_path=$(zenity --file-selection --file-filter="Backup (*.zip *.json) | *.zip *.json" --title="Select Key Commands Backup File" 2>/dev/null) || true
                elif command -v kdialog >/dev/null 2>&1; then
                    import_path=$(kdialog --getopenfilename "$HOME/Downloads" "*.zip *.json" --title="Select Key Commands Backup File" 2>/dev/null) || true
                fi
            fi
            if [ -z "$import_path" ]; then
                read -p "Enter the path to your shortcut backup (.zip or .json): " import_path
            fi
            
            if [ -f "$import_path" ]; then
                IMPORT_SHORTCUTS_PATH="$import_path"
                echo -e "  [${green}SUCCESS${reset}] File found. Will import during integration."
            else
                echo -e "  [${red}ERROR${reset}] File does not exist. Skipping import."
            fi
            sleep 2
        fi
    fi
else
    # Auto accept mode
    SET_MANAGE="false"
    SET_MANUAL_DPI="96"
    SET_MATCH_PHYS="false"
    SET_FREETYPE="40"
fi

# Write configurations
set_config_val "manage_graphics" "$SET_MANAGE"
set_config_val "manual_dpi" "$SET_MANUAL_DPI"
set_config_val "match_physical_dpi" "$SET_MATCH_PHYS"
set_config_val "freetype_interpreter" "$SET_FREETYPE"

# Asset Validation (SDA and MediaBay are required for software installs)
if [ "$INSTALL_SOFTWARE" = true ]; then
    echo "Validating installers..."
    mkdir -p "$TORQUIO_INSTALLERS_DIR"
    SEARCH_DIRS=("$TORQUIO_INSTALLERS_DIR" "$HOME/Downloads" "$PWD")
    
    FOUND_MEDIABAY=$(find "${SEARCH_DIRS[@]}" -maxdepth 1 -type f -name "MediaBay_Installer_win64*.zip" 2>/dev/null | sort -V | tail -n 1)
    FOUND_SDA=$(find "${SEARCH_DIRS[@]}" -maxdepth 1 -type f -name "Steinberg_Download_Assistant_*_Installer_win*.exe" 2>/dev/null | sort -V | tail -n 1)
    FOUND_NP=$(find "${SEARCH_DIRS[@]}" -maxdepth 1 -type f -name "NotePerformer-Installer-*.exe" 2>/dev/null | sort -V | tail -n 1)
    
    MISSING_MANDATORY=false
    if [ -z "$FOUND_MEDIABAY" ]; then
        echo -e "  [${red}MISSING${reset}] Mandatory: MediaBay_Installer_win64.zip"
        MISSING_MANDATORY=true
    fi
    if [ -z "$FOUND_SDA" ]; then
        echo -e "  [${red}MISSING${reset}] Mandatory: Steinberg_Download_Assistant_*_Installer_win*.exe"
        MISSING_MANDATORY=true
    fi
    
    if [ "$MISSING_MANDATORY" = true ]; then
        echo ""
        echo -e "${red}Error: Mandatory installers were not found.${reset}"
        echo "Please place them in $TORQUIO_INSTALLERS_DIR or ~/Downloads and run this script again."
        exit 1
    fi
fi

# Confirm Install manifest
print_wizard_banner
echo -e "${blue}=== Installation Manifest ===${reset}"
manifest_manage_str="${wine}$SET_MANAGE${reset}"
if [ "$XDG_SESSION_TYPE" = "x11" ]; then
    manifest_manage_str="${gray}N/A (Wayland Only)${reset}"
fi
echo -e "  - Graphics Management:        $manifest_manage_str"
echo -e "  - Target Wine DPI:            ${wine}$SET_MANUAL_DPI DPI${reset}"
echo -e "  - FreeType Interpreter:       ${wine}v$SET_FREETYPE${reset}"
if [ -n "$MAPPED_FOLDER_PATH" ]; then
    type_str="Network Drive"
    if [ "$MAPPED_FOLDER_TYPE" = "desktop" ]; then
        type_str="Desktop Shortcut"
    fi
    echo -e "  - Map Local Folder:           ${wine}$MAPPED_FOLDER_PATH${reset} (as $type_str)"
fi
if [ -n "$IMPORT_SHORTCUTS_PATH" ]; then
    echo -e "  - Import Shortcuts:           ${wine}$(basename "$IMPORT_SHORTCUTS_PATH")${reset}"
fi
if [ "$INSTALL_SOFTWARE" = true ]; then
    echo -e "  - MediaBay Installer:         ${wine}$(basename "$FOUND_MEDIABAY")${reset}"
    echo -e "  - SDA Installer:              ${wine}$(basename "$FOUND_SDA")${reset}"
    if [ -n "$FOUND_NP" ]; then
        echo -e "  - NotePerformer Installer:    ${wine}$(basename "$FOUND_NP")${reset}"
    else
        echo -e "  - NotePerformer Installer:    ${gray}Not found (skipping)${reset}"
    fi
fi
echo -e "${blue}=============================${reset}"
echo ""

if [ "$AUTO_ACCEPT" = false ]; then
    read -p "Proceed with the wizard installation tasks? [Y/n]: " confirm_install
    if [[ "$confirm_install" =~ ^[Nn]$ ]]; then
        echo -e "${red}Installation cancelled.${reset}"
        exit 10
    fi
fi

# Execution of selected phases
if [ "$CREATE_CONTAINER" = true ]; then
    echo "Phase 1: Creating Distrobox container ($TORQUIO_CONTAINER_NAME)..."
    if distrobox list 2>/dev/null | grep -q "$TORQUIO_CONTAINER_NAME"; then
        echo "Container $TORQUIO_CONTAINER_NAME already exists. Skipping creation."
    else
        distrobox create -i ubuntu:24.04 -n "$TORQUIO_CONTAINER_NAME" --yes
    fi
fi

WORKSPACE_DIR="$SCRIPT_DIR"

if [ "$BUILD_WINE" = true ]; then
    echo "Phase 2: Compiling Wine Engine..."
    distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "cd \"$WORKSPACE_DIR\" && ./scripts/1-build/build_wine.sh"
fi

if [ "$SETUP_PREFIX" = true ]; then
    echo "Phase 3: Initializing Wine Prefix..."
    distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "cd \"$WORKSPACE_DIR\" && ./scripts/2-install/setup_prefix.sh"
fi

if [ "$INSTALL_SOFTWARE" = true ]; then
    echo "Phase 4: Installing Steinberg Components..."
    echo "Installing MediaBay..."
    distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "cd \"$WORKSPACE_DIR\" && ./scripts/2-install/install_mediabay.sh"
    echo "Installing SDA..."
    distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "cd \"$WORKSPACE_DIR\" && ./scripts/2-install/install_sda.sh"
    if [ -n "$FOUND_NP" ]; then
        echo "Installing NotePerformer..."
        distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "cd \"$WORKSPACE_DIR\" && ./scripts/2-install/install_noteperformer.sh"
    fi
    echo "Extracting Desktop Icons..."
    distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "cd \"$WORKSPACE_DIR\" && ./scripts/2-install/extract_icons.sh --initial"
fi

if [ "$INTEGRATE" = true ]; then
    echo "Phase 5: Performing Host Integration..."
    mkdir -p "$HOME/.local/bin"
    rm -f "$HOME/.local/bin/torquio" "$HOME/.local/bin/torquio-dorico" "$HOME/.local/bin/torquio-sam" "$HOME/.local/bin/torquio-sda-handler"
    
    echo "Installing torquio orchestrator to ~/.local/bin/torquio..."
    ln -s "$SCRIPT_DIR/torquio" "$HOME/.local/bin/torquio"
    
    for handler in "$SCRIPT_DIR/scripts/3-runtime_handlers/"torquio*; do
        base_name=$(basename "$handler")
        if [ "$base_name" = "torquio-sda-handler" ]; then
            sed "s|@TORQUIO_REPO_DIR@|$SCRIPT_DIR|g" "$handler" > "$HOME/.local/bin/$base_name"
        else
            cp "$handler" "$HOME/.local/bin/"
        fi
    done
    chmod +x "$HOME/.local/bin/"torquio*
    
    mkdir -p "$HOME/.local/share/applications"
    echo "Registering MIME types..."
    mkdir -p "$HOME/.local/share/mime/packages"
    cp "$SCRIPT_DIR/desktop_stubs/application-x-dorico.xml" "$HOME/.local/share/mime/packages/"
    update-mime-database "$HOME/.local/share/mime/" || true
fi

# Apply Mapped Folders if configured
if [ -n "$MAPPED_FOLDER_PATH" ] && [ -d "$TORQUIO_PREFIX_DIR/dosdevices" ]; then
    real_map_path=$(realpath "$MAPPED_FOLDER_PATH")
    if [ "$MAPPED_FOLDER_TYPE" = "desktop" ]; then
        desktop_dir="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
        if [ -f "$HOME/.config/user-dirs.dirs" ]; then
            source "$HOME/.config/user-dirs.dirs" 2>/dev/null || true
            desktop_dir="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
        fi
        mkdir -p "$desktop_dir"
        folder_name=$(basename "$real_map_path")
        dest_link="$desktop_dir/$folder_name"
        
        if [ -e "$dest_link" ] && [ ! -L "$dest_link" ]; then
            read -p "A physical file/folder named '$folder_name' already exists on your Desktop. Enter a custom shortcut name: " custom_name
            if [ -z "$custom_name" ]; then
                custom_name="${folder_name}-shortcut"
            fi
            dest_link="$desktop_dir/$custom_name"
        fi
        rm -f "$dest_link"
        ln -sf "$real_map_path" "$dest_link"
        echo "Mapped '$real_map_path' to Desktop shortcut: $(basename "$dest_link")"
    else
        drive_letter=""
        for letter in d e f g h i j k l m n o p q r s t u v w x y z; do
            if [ ! -e "$TORQUIO_PREFIX_DIR/dosdevices/${letter}:" ]; then
                drive_letter="${letter}:"
                break
            fi
        done
        if [ -n "$drive_letter" ]; then
            ln -sf "$real_map_path" "$TORQUIO_PREFIX_DIR/dosdevices/$drive_letter"
            echo "Mapped '$real_map_path' to Wine drive ${drive_letter^^}\\"
        fi
    fi
fi

# Apply Keyboard Shortcuts Import if configured
if [ -n "$IMPORT_SHORTCUTS_PATH" ] && [ -f "$IMPORT_SHORTCUTS_PATH" ]; then
    echo "Staging keyboard shortcuts from $IMPORT_SHORTCUTS_PATH..."
    rm -rf "$TORQUIO_DATA_DIR/staged_keycommands"
    rm -f "$TORQUIO_DATA_DIR"/staged_keycommands.*
    mkdir -p "$TORQUIO_DATA_DIR/staged_keycommands"
    
    if [[ "$IMPORT_SHORTCUTS_PATH" =~ \.zip$ ]]; then
        unzip -o "$IMPORT_SHORTCUTS_PATH" -d "$TORQUIO_DATA_DIR/staged_keycommands/" >/dev/null 2>&1 || true
    else
        cp "$IMPORT_SHORTCUTS_PATH" "$TORQUIO_DATA_DIR/staged_keycommands/"
    fi
    echo "Keyboard shortcuts staged. They will be automatically imported the first time Dorico is launched."
fi

# Apply Wine registry entries for scale parameters immediately
if [ -d "$TORQUIO_PREFIX_DIR" ] && distrobox list 2>/dev/null | grep -q "$TORQUIO_CONTAINER_NAME"; then
    apply_dpi="$SET_MANUAL_DPI"
    if [ "$SET_MANAGE" = "true" ] && [ "$XDG_SESSION_TYPE" != "x11" ]; then
        graphics_json=$(python3 "$SCRIPT_DIR/scripts/3-runtime_handlers/torquio_graphics.py" 2>/dev/null || true)
        q_dpi=$(echo "$graphics_json" | grep -o '"target_wine_dpi": [0-9]*' | cut -d' ' -f2 || true)
        if [ -n "$q_dpi" ] && [ "$q_dpi" -gt 0 ]; then
            apply_dpi="$q_dpi"
        fi
    fi
    echo "Applying configured Wine prefix settings immediately..."
    distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "export WINEPREFIX=\"$TORQUIO_PREFIX_DIR\"; export PATH=\"$WINE_CUSTOM_BIN:\$PATH\"; export FREETYPE_PROPERTIES=\"truetype:interpreter-version=$SET_FREETYPE\"; wine reg add \"HKCU\\Control Panel\\Desktop\" /v LogPixels /t REG_DWORD /d $apply_dpi /f" >/dev/null 2>&1 || true
    distrobox enter "$TORQUIO_CONTAINER_NAME" -- bash -c "export WINEPREFIX=\"$TORQUIO_PREFIX_DIR\"; export PATH=\"$WINE_CUSTOM_BIN:\$PATH\"; wineserver -k && wineserver -w" >/dev/null 2>&1 || true
fi

if [ "$ACTION" = "install" ] || [ "$ACTION" = "resume" ]; then
    echo ""
    echo "==========================================="
    echo "   Software Download Phase                 "
    echo "==========================================="
    echo "Opening the Steinberg Download Assistant (SDA)..."
    nohup "$HOME/.local/bin/torquio-sda-handler" > /dev/null 2>&1 &
fi
# Clean up any virtual/unfunctional Windows desktop shortcuts created by installers
clean_desktop_lnk

echo ""
echo "================================================================"
echo "               Torquio Setup Wizard Complete!                   "
echo "================================================================"
echo "All interactive wizard installation tasks completed successfully."
echo "================================================================"
echo ""
