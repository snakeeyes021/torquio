#!/bin/bash
VALERIO_CONTAINER_NAME="valerio-env"
VALERIO_PREFIX_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/valerio/prefix"
WINE_CUSTOM_BIN="/opt/wine-custom/bin"

FILE_ARG=""
if [ -n "$1" ]; then
    # We must translate the Linux path to a Windows path *inside* the container's wine environment
    WIN_PATH=$(distrobox enter "$VALERIO_CONTAINER_NAME" -- bash -c "export WINEDEBUG=-all; export WINEPREFIX=\"$VALERIO_PREFIX_DIR\"; export PATH=\"$WINE_CUSTOM_BIN:\$PATH\"; winepath -w \"$1\"" | tr -d '\r')
    FILE_ARG=" \"$WIN_PATH\""
fi

distrobox enter "$VALERIO_CONTAINER_NAME" -- bash -c "export WINEPREFIX=\"$VALERIO_PREFIX_DIR\"; export WINEDLLOVERRIDES=\"winemenubuilder.exe=d\"; export PATH=\"$WINE_CUSTOM_BIN:\$PATH\"; cd \"$VALERIO_PREFIX_DIR/drive_c/Program Files/Steinberg/Dorico6\"; wine 'Dorico6.exe'$FILE_ARG"
