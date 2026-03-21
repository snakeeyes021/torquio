#!/bin/bash
set -e

# Find the NotePerformer installer in the current directory (generalized glob)
# This handles the personalized filenames [User Name ID] that vary by customer.
INSTALLER=$(ls NotePerformer-Installer-*.exe 2>/dev/null | head -n 1)

if [ -z "$INSTALLER" ]; then
    echo "Error: Could not find any NotePerformer-Installer-*.exe in the current directory."
    exit 1
fi

echo "Found NotePerformer installer: $INSTALLER"

# Run it inside the container using our custom Wine
distrobox enter dorico-box -- bash -c "export WINEPREFIX=\"\$HOME/dev/steinberg-on-linux/dorico-prefix\"; export PATH=\"/opt/wine-custom/bin:\$PATH\"; cd \"\$HOME/dev/steinberg-on-linux\"; wine \"$INSTALLER\""
