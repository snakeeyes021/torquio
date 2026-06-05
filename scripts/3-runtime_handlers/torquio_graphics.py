#!/usr/bin/env python3
import os
import subprocess
import json
import re
import sys
import math

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        return result.stdout.strip()
    except Exception:
        return ""

def get_edid_dpi(connector, w_px, h_px):
    # Try to find the physical dimensions from sysfs
    base_dir = "/sys/class/drm"
    if not os.path.isdir(base_dir):
        return 96
    
    for d in os.listdir(base_dir):
        if d.endswith(f"-{connector}") or connector in d:
            edid_path = os.path.join(base_dir, d, "edid")
            if os.path.isfile(edid_path) and os.path.getsize(edid_path) > 20:
                try:
                    with open(edid_path, "rb") as f:
                        edid = f.read()
                        # EDID version 1.3/1.4 physical size is at bytes 21 and 22 in centimeters
                        width_cm = edid[21]
                        height_cm = edid[22]
                        if width_cm > 0 and height_cm > 0:
                            w_inch = width_cm * 0.393701
                            h_inch = height_cm * 0.393701
                            diag_inch = math.sqrt(w_inch**2 + h_inch**2)
                            diag_px = math.sqrt(w_px**2 + h_px**2)
                            return int(round(diag_px / diag_inch))
                except Exception:
                    pass
    return 96

def query_gnome():
    out = run_cmd("dbus-send --session --print-reply --dest=org.gnome.Mutter.DisplayConfig /org/gnome/Mutter/DisplayConfig org.gnome.Mutter.DisplayConfig.GetCurrentState")
    
    if not out:
        return None
        
    scale = 1.0
    connector = ""
    w_px = 0
    h_px = 0
    
    logical_monitor_pattern = re.compile(
        r'int32\s+-?\d+\s+int32\s+-?\d+\s+double\s+([\d\.]+)\s+uint32\s+\d+\s+boolean\s+(true)\s+array\s+\[\s+struct\s+\{\s+string\s+"([^"]+)"',
        re.DOTALL
    )
    match = logical_monitor_pattern.search(out)
    if match:
        scale = float(match.group(1))
        connector = match.group(3)
        
    if connector:
        # Find physical monitor modes for this connector
        # A bit hacky: find the connector string, then find the mode where is-current is true
        parts = out.split(f'string "{connector}"')
        if len(parts) > 1:
            block = parts[1]
            modes_block = block.split('array [')[1]
            # split by struct
            structs = modes_block.split('struct {')
            for s in structs:
                if 'string "is-current"' in s and 'boolean true' in s:
                    res_match = re.search(r'int32\s+(\d+)\s+int32\s+(\d+)', s)
                    if res_match:
                        w_px = int(res_match.group(1))
                        h_px = int(res_match.group(2))
                        break

    if w_px == 0:
        return None
        
    phys_dpi = get_edid_dpi(connector, w_px, h_px)
    return {
        "de": "GNOME",
        "supported": True,
        "connector": connector,
        "width": w_px,
        "height": h_px,
        "scale": scale,
        "physical_dpi": phys_dpi,
        "ideal_xwayland_policy": "Partially Scaled",
        "target_wine_dpi": int(round(phys_dpi / scale))
    }

def query_kde():
    out = run_cmd("kscreen-doctor -o")
    if not out:
        return None
    
    # Parse priority 1
    blocks = out.split("Output: ")
    for block in blocks[1:]:
        if "priority 1" in block or "priority: 1" in block or "primary" in block: # Fallback just in case
            lines = block.split("\n")
            connector = lines[0].split()[1] if len(lines[0].split()) > 1 else "Unknown"
            
            scale = 1.0
            w_px = 0
            h_px = 0
            
            for line in lines:
                if "Scale:" in line:
                    scale_match = re.search(r'Scale:\s*([\d\.]+)', line)
                    if scale_match:
                        scale = float(scale_match.group(1))
                elif "Modes:" in line:
                    pass
                elif "*" in line and "x" in line and "@" in line:
                    res_match = re.search(r'(\d+)x(\d+)@', line)
                    if res_match:
                        w_px = int(res_match.group(1))
                        h_px = int(res_match.group(2))
            
            if w_px > 0:
                phys_dpi = get_edid_dpi(connector, w_px, h_px)
                return {
                    "de": "KDE",
                    "supported": True,
                    "connector": connector,
                    "width": w_px,
                    "height": h_px,
                    "scale": scale,
                    "physical_dpi": phys_dpi,
                    "ideal_xwayland_policy": "Apply scaling themselves",
                    "target_wine_dpi": phys_dpi
                }
    return None

def query_cosmic():
    out = run_cmd("cosmic-randr list")
    if not out:
        return None
        
    blocks = out.split("\n\n")
    for block in blocks:
        if "Xwayland primary: true" in block:
            lines = block.split("\n")
            connector = lines[0].strip(': ')
            scale = 1.0
            w_px = 0
            h_px = 0
            
            for line in lines:
                if "Scale:" in line:
                    scale_match = re.search(r'Scale:\s*([\d\.]+)%', line)
                    if scale_match:
                        scale = float(scale_match.group(1)) / 100.0
                elif "(current)" in line:
                    res_match = re.search(r'(\d+)x(\d+)', line)
                    if res_match:
                        w_px = int(res_match.group(1))
                        h_px = int(res_match.group(2))
            
            if w_px > 0:
                phys_dpi = get_edid_dpi(connector, w_px, h_px)
                return {
                    "de": "COSMIC",
                    "supported": True,
                    "connector": connector,
                    "width": w_px,
                    "height": h_px,
                    "scale": scale,
                    "physical_dpi": phys_dpi,
                    "ideal_xwayland_policy": "Optimize for gaming",
                    "target_wine_dpi": phys_dpi
                }
    return None

def main():
    de = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
    
    result = None
    if "GNOME" in de:
        result = query_gnome()
    elif "KDE" in de:
        result = query_kde()
    elif "COSMIC" in de:
        result = query_cosmic()
        
    if not result:
        # Fallback or unsupported
        result = {
            "de": de if de else "Unknown",
            "supported": False
        }
        
    print(json.dumps(result))

if __name__ == "__main__":
    main()
