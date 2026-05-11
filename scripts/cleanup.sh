#!/bin/bash
# Valerio Cleanup / Uninstaller Script
# This script wipes the Valerio environment including the container, data, and cache.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

echo "⚠️  WARNING: This will permanently delete the following:"
echo " - Distrobox container: $VALERIO_CONTAINER_NAME"
echo " - Data directory: $VALERIO_DATA_DIR (includes Wine prefix)"
echo " - Cache directory: $VALERIO_CACHE_DIR (includes Wine source code and compilation artifacts)"
echo " - Host integration scripts and .desktop files"
echo ""
read -p "Are you sure you want to continue? (y/N): " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
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
rm -f "$HOME/.local/share/applications/Dorico 6.desktop"
rm -f "$HOME/.local/share/applications/Steinberg Activation Manager.desktop"
rm -f "$HOME/.local/share/applications/steinberg-sda-handler.desktop"

echo "Updating desktop database..."
update-desktop-database "$HOME/.local/share/applications/" || true

echo "Cleanup complete! The Valerio environment has been wiped."
