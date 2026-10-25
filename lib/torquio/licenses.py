"""Which licenses are activated in a Torquio Wine prefix (the uninstaller's guard and the log export use this).

Steinberg: the Activation Manager keeps each product package and its licensed items in activation.dat. An
item activated on this computer carries a license token ("jwt"); deactivating (or signing out of the
Activation Manager, which deactivates everything) empties the tokens or the package list.

Plug-ins:
- Cantai keeps its activation as "activationToken" in AppData/Roaming/Cantai/Cantai.settings (an XML file);
  deactivating it in Cantai empties the token.
"""
import glob
import json
import os
import re

ACTIVATION_DAT = "Steinberg/Activation Manager/Data/activation.dat"


def steinberg_state(prefix):
    """One of:
        active             at least one license is activated; followed by one product name per line
        inactive           nothing is activated
        unknown <reason>   the state couldn't be determined
    """
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


def cantai_active(drive_c):
    for path in glob.glob(os.path.join(drive_c, "users", "*", "AppData", "Roaming", "Cantai", "Cantai.settings")):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        if re.search(r'name="activationToken"\s+val="[^"]+"', text):
            return True
    return False


def active_plugins(prefix):
    """[(name, where to deactivate it)] for each third-party plug-in with an activated license."""
    drive_c = os.path.join(prefix, "drive_c")
    active = []
    if cantai_active(drive_c):
        active.append(("Cantai", "in Cantai itself"))
    return active


def format_plugins(plugins):
    """One "NAME<TAB>where to deactivate it" line per plug-in (what the Bash callers parse)."""
    return "\n".join(f"{name}\t{where}" for name, where in plugins)
