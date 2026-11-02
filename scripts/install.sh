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
torquio_require_python

# The installer itself: lib/torquio/cli/install.py (exit code 10 when the user cancels)
torquio_py install "$@"
