#!/usr/bin/env python3
"""List third-party plug-ins whose license is activated in a Torquio Wine prefix.

- Cantai keeps its activation as "activationToken" in AppData/Roaming/Cantai/Cantai.settings (an XML file);
  deactivating it in Cantai empties the token.

Usage: plugin_license_state.py PREFIX
Prints the name of each plug-in with an activated license, one per line (nothing if there are none).
"""
import glob
import os
import re
import sys


def cantai_active(drive_c):
    for path in glob.glob(os.path.join(drive_c, "users", "*", "AppData", "Roaming", "Cantai", "Cantai.settings")):
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if re.search(r'name="activationToken"\s+val="[^"]+"', text):
            return True
    return False


def main(prefix):
    drive_c = os.path.join(prefix, "drive_c")
    active = []
    if cantai_active(drive_c):
        active.append("Cantai")
    return active


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    for name in main(sys.argv[1]):
        print(name)
