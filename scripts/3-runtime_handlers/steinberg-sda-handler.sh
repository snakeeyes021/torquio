#!/bin/bash
VALERIO_CONTAINER_NAME="valerio-env"
VALERIO_PREFIX_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/valerio/prefix"
WINE_CUSTOM_BIN="/opt/wine-custom/bin"
VALERIO_REPO_DIR="@VALERIO_REPO_DIR@"

URL="$1"

# Ensure log directory exists
mkdir -p "$HOME/.local/share/valerio"

# Start background watcher for Dorico installation if the icon is not yet set
ICON_FILE="$HOME/.local/share/icons/hicolor/256x256/apps/valerio-dorico.png"
if [ ! -f "$ICON_FILE" ]; then
    (
        echo "Dorico icon not detected. Starting background watcher for Dorico installation..."
        
        # Clean up old status files to avoid stale matches
        find "$VALERIO_PREFIX_DIR/drive_c/users" -path "*/AppData/Local/Temp/*" -name "*.json" -delete 2>/dev/null || true
        
        while true; do
            # 1. Check if Dorico success status file has been written
            DORICO_STATUS_FILE=$(find "$VALERIO_PREFIX_DIR/drive_c/users" -path "*/AppData/Local/Temp/*" -name "*Dorico*Application*Installer.json" 2>/dev/null | head -n 1)
            
            if [ -n "$DORICO_STATUS_FILE" ] && [ -f "$DORICO_STATUS_FILE" ]; then
                artifactId=$(grep -o '"artifactId":\s*"[^"]*"' "$DORICO_STATUS_FILE" | head -n 1 | cut -d'"' -f4)
                success=$(grep -o '"success":\s*\(true\|false\)' "$DORICO_STATUS_FILE" | head -n 1 | cut -d':' -f2 | tr -d '[:space:]')
                
                if [[ "$artifactId" =~ Dorico.*Application_Installer ]] && [ "$success" = "true" ]; then
                    echo "Dorico installation success detected! Extracting icons..."
                    # Run the extraction script inside the container
                    distrobox enter "$VALERIO_CONTAINER_NAME" -- bash -c "cd \"$VALERIO_REPO_DIR\" && ./scripts/2-install/extract_icons.sh"
                    break
                fi
            fi
            
            # 2. Check if the SDA processes have terminated (fallback in case of exit/cancel without installing)
            if ! distrobox enter "$VALERIO_CONTAINER_NAME" -- bash -c "ps auxww" | grep -iE "Steinberg Download Assistant\.exe|STEI~B2R\.EXE|aria2c\.exe" > /dev/null; then
                echo "SDA processes terminated. Exiting watcher."
                break
            fi
            
            sleep 4
        done
    ) > "$HOME/.local/share/valerio/sda_watcher.log" 2>&1 &
fi

# Now run the actual SDA in the foreground (it will block the terminal/handler)
if [ -n "$URL" ]; then
    # Launched by browser (link provided) - pass the URL directly without --redirect
    distrobox enter "$VALERIO_CONTAINER_NAME" -- bash -c "export WINEPREFIX=\"$VALERIO_PREFIX_DIR\"; export WINEDLLOVERRIDES=\"winemenubuilder.exe=d\"; export PATH=\"$WINE_CUSTOM_BIN:\$PATH\"; wine 'C:\\Program Files (x86)\\Steinberg\\Download Assistant\\Steinberg Download Assistant.exe' '$URL'"
else
    # Standard launch (no link)
    distrobox enter "$VALERIO_CONTAINER_NAME" -- bash -c "export WINEPREFIX=\"$VALERIO_PREFIX_DIR\"; export WINEDLLOVERRIDES=\"winemenubuilder.exe=d\"; export PATH=\"$WINE_CUSTOM_BIN:\$PATH\"; wine 'C:\\Program Files (x86)\\Steinberg\\Download Assistant\\Steinberg Download Assistant.exe'"
fi

