#!/usr/bin/env python3
"""Report whether any Steinberg license is activated in a Torquio Wine prefix.

The Steinberg Activation Manager keeps each product package and its licensed items in activation.dat.
An item activated on this computer carries a license token ("jwt"); deactivating (or signing out of the
Activation Manager, which deactivates everything) empties the tokens or the package list.

Usage: steinberg_license_state.py PREFIX
Prints one of:
    active             at least one license is activated; followed by one product name per line
    inactive           nothing is activated
    unknown <reason>   the state couldn't be determined
"""
import glob
import json
import os
import sys

ACTIVATION_DAT = "Steinberg/Activation Manager/Data/activation.dat"


def main(prefix):
    drive_c = os.path.join(prefix, "drive_c")
    if not os.path.isdir(drive_c):
        return "inactive"
    files = glob.glob(os.path.join(drive_c, "users", "*", "AppData", "Roaming", ACTIVATION_DAT))
    files += glob.glob(os.path.join(drive_c, "ProgramData", ACTIVATION_DAT))
    if not files:
        if os.path.isdir(os.path.join(drive_c, "Program Files", "Steinberg", "Activation Manager")):
            return "unknown the Activation Manager is installed but has no activation data"
        return "inactive"
    active = []
    for path in files:
        try:
            with open(path, encoding="utf-8-sig") as f:
                packages = json.load(f).get("ProductPackages", [])
        except (OSError, ValueError, AttributeError) as e:
            return f"unknown couldn't read {path} ({type(e).__name__})"
        for package in packages:
            if any(item.get("jwt") for item in package.get("LicensedItems", [])):
                name = package.get("ProductPackage") or package.get("GrantID") or "unnamed product"
                if name not in active:
                    active.append(name)
    return "\n".join(["active"] + active) if active else "inactive"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(main(sys.argv[1]))
