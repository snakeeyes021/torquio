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
torquio_require_python

# The uninstaller itself: lib/torquio/cli/uninstall.py (exit code 10 when the user cancels)
torquio_py uninstall
