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

def should_match_physical_dpi():
    config_path = os.path.expanduser("~/.config/torquio/config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                d = json.load(f)
                val = d.get("match_physical_dpi", False)
                if isinstance(val, str):
                    return val.lower() in ("true", "1")
                return bool(val)
        except Exception:
            pass
    return False

def get_edid_dpi(connector, w_px, h_px):
    # Try to find the physical dimensions from sysfs
    base_dir = "/sys/class/drm"
    if not os.path.isdir(base_dir):
        return 96
    
    for d in os.listdir(base_dir):
        if "-" in d:
            parts = d.split("-", 1)
            conn_name = parts[1]
            if conn_name == connector or conn_name.startswith(f"{connector}-") or connector.startswith(f"{conn_name}-"):
                edid_path = os.path.join(base_dir, d, "edid")
                if os.path.isfile(edid_path):
                    try:
                        with open(edid_path, "rb") as f:
                            edid = f.read()
                            
                            # 1. Try millimeter precision from Detailed Timing Descriptor #1 (byte 54+)
                            if len(edid) >= 128 and (edid[54] != 0 or edid[55] != 0):
                                w_mm = ((edid[68] & 0xF0) << 4) | edid[66]
                                if w_mm > 0:
                                    return int(round(w_px / (w_mm / 25.4)))
                                    
                            # 2. Fall back to centimeter-level diagonal calculation from basic parameters
                            if len(edid) > 22:
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
        idx = out.find(f'string "{connector}"')
        if idx != -1:
            sub_out = out[idx:]
            structs = sub_out.split('struct {')
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
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    match_physical = should_match_physical_dpi()

    if session_type == "x11":
        return {
            "de": "GNOME",
            "supported": False,
            "connector": connector,
            "width": w_px,
            "height": h_px,
            "scale": scale,
            "physical_dpi": phys_dpi,
            "ideal_xwayland_policy": "N/A (Native X11 Session)",
            "target_wine_dpi": 96,
            "target_xwayland_factor": 1,
            "rec_formula": "Manual Configuration Required (X11 auto-scaling unsupported)"
        }
        
    is_integer_scale = (scale == round(scale))
    if match_physical:
        if is_integer_scale:
            target_dpi = max(96, phys_dpi)
            target_factor = int(scale)
            ideal_policy = f"Native Integer Scaling (xwayland-scaling-factor={target_factor})" if scale > 1.0 else "Native (no scaling)"
            rec_formula = f"Formula: WINE DPI matches physical ideal DPI ({target_dpi} DPI)"
        else:
            target_dpi = max(96, int(round(phys_dpi / scale)))
            target_factor = 1
            ideal_policy = "Framebuffer Upscale (xwayland-scaling-factor=1)" if scale > 1.0 else "Native (no scaling)"
            rec_formula = f"Formula: {phys_dpi} physical ideal DPI / {scale}x GNOME upscale = {target_dpi} target DPI"
    else:
        if is_integer_scale:
            target_dpi = int(round(96 * scale))
            target_factor = int(scale)
            ideal_policy = f"Native Integer Scaling (xwayland-scaling-factor={target_factor})" if scale > 1.0 else "Native (no scaling)"
            rec_formula = f"Formula: Standard 96 DPI baseline * {scale}x scale = {target_dpi} target DPI"
        else:
            target_dpi = 96
            target_factor = 1
            ideal_policy = "Framebuffer Upscale (xwayland-scaling-factor=1)" if scale > 1.0 else "Native (no scaling)"
            rec_formula = "Formula: Standard 96 DPI baseline (compositor upscales UI)"

    return {
        "de": "GNOME",
        "supported": True,
        "connector": connector,
        "width": w_px,
        "height": h_px,
        "scale": scale,
        "physical_dpi": phys_dpi,
        "ideal_xwayland_policy": ideal_policy,
        "target_wine_dpi": target_dpi,
        "target_xwayland_factor": target_factor,
        "rec_formula": rec_formula
    }

def query_kde():
    out = run_cmd("kscreen-doctor -o")
    if not out:
        return None
    
    # Parse priority 1 or fall back to the first available output block
    blocks = [b for b in out.split("Output: ")[1:] if b.strip()]
    if not blocks:
        return None
        
    target_block = None
    for block in blocks:
        if "priority 1" in block or "priority: 1" in block or "primary" in block:
            target_block = block
            break
    if not target_block:
        target_block = blocks[0]
        
    lines = target_block.split("\n")
    # Retrieve connector name using regex (Output: was stripped during split)
    connector_match = re.search(r'^\s*(?:\d+\s+)?(\S+)', lines[0])
    used_connector = connector_match.group(1) if connector_match else "Unknown"
    
    scale = 1.0
    w_px = 0
    h_px = 0
    
    for line in lines:
        if "Scale:" in line:
            scale_match = re.search(r'Scale:\s*([\d\.]+)', line)
            if scale_match:
                scale = float(scale_match.group(1))
        elif "Geometry:" in line:
            geom_match = re.search(r'Geometry:\s*-?\d+,-?\d+\s+(\d+)x(\d+)', line)
            if geom_match:
                w_px = int(geom_match.group(1))
                h_px = int(geom_match.group(2))
        
        # Check all lines for the current mode marker '*'
        if "*" in line and "x" in line:
            res_match = re.search(r'(\d+)x(\d+)', line)
            if res_match:
                w_px_mode = int(res_match.group(1))
                h_px_mode = int(res_match.group(2))
                # Only use modes resolution if Geometry didn't successfully set it
                if w_px == 0:
                    w_px = w_px_mode
                    h_px = h_px_mode
                    
    if w_px == 0:
        for line in lines:
            if "x" in line:
                res_match = re.search(r'(\d+)x(\d+)', line)
                if res_match:
                    w_px = int(res_match.group(1))
                    h_px = int(res_match.group(2))
                    break
                    
    if w_px == 0:
        w_px = 1920
        h_px = 1080
        
    phys_dpi = get_edid_dpi(used_connector, w_px, h_px)
    match_physical = should_match_physical_dpi()
    if match_physical:
        target_dpi = max(96, phys_dpi)
        rec_formula = f"Formula: {phys_dpi} physical ideal DPI (Scale XWayland clients themselves)"
    else:
        target_dpi = max(96, int(round(96 * scale)))
        rec_formula = f"Formula: Standard 96 DPI baseline * {scale}x scale = {target_dpi} target DPI"
        
    return {
        "de": "KDE",
        "supported": True,
        "connector": used_connector,
        "width": w_px,
        "height": h_px,
        "scale": scale,
        "physical_dpi": phys_dpi,
        "ideal_xwayland_policy": "Scale XWayland clients themselves (XwaylandClientsScale=true)" if scale > 1.0 else "Native (no scaling)",
        "target_wine_dpi": target_dpi,
        "target_xwayland_factor": 1,
        "rec_formula": rec_formula
    }

def query_cosmic():
    out = run_cmd("cosmic-randr list")
    if not out:
        return None
        
    # Group output by unindented lines to prevent splitting metadata from mode details
    lines = out.splitlines()
    blocks = []
    current_connector = None
    current_lines = []
    
    for line in lines:
        if not line.strip():
            continue
        if not line.startswith(" ") and not line.startswith("\t"):
            if current_connector:
                blocks.append((current_connector, current_lines))
            current_connector = line.split()[0].strip(':') if line.split() else "Unknown"
            current_lines = [line]
        else:
            current_lines.append(line)
            
    if current_connector:
        blocks.append((current_connector, current_lines))
        
    if not blocks:
        return None
        
    target_connector = None
    target_lines = None
    for connector, b_lines in blocks:
        block_text = "\n".join(b_lines)
        if "Xwayland primary: true" in block_text or "Xwayland primary: True" in block_text:
            target_connector = connector
            target_lines = b_lines
            break
            
    if not target_connector:
        target_connector = blocks[0][0]
        target_lines = blocks[0][1]
        
    scale = 1.0
    w_px = 0
    h_px = 0
    
    for line in target_lines:
        if "Scale:" in line:
            scale_match = re.search(r'Scale:\s*([\d\.]+)%', line)
            if scale_match:
                scale = float(scale_match.group(1)) / 100.0
        elif "(current)" in line:
            res_match = re.search(r'(\d+)x(\d+)', line)
            if res_match:
                w_px = int(res_match.group(1))
                h_px = int(res_match.group(2))
                
    if w_px == 0:
        for line in target_lines:
            if "x" in line and ("@" in line or "Hz" in line):
                res_match = re.search(r'(\d+)x(\d+)', line)
                if res_match:
                    w_px = int(res_match.group(1))
                    h_px = int(res_match.group(2))
                    break
                    
    if w_px == 0:
        w_px = 1920
        h_px = 1080
        
    phys_dpi = get_edid_dpi(target_connector, w_px, h_px)
    match_physical = should_match_physical_dpi()
    if match_physical:
        target_dpi = max(96, phys_dpi)
        rec_formula = f"Formula: {phys_dpi} physical ideal DPI (Scale XWayland clients themselves)"
    else:
        target_dpi = max(96, int(round(96 * scale)))
        rec_formula = f"Formula: Standard 96 DPI baseline * {scale}x scale = {target_dpi} target DPI"
        
    return {
        "de": "COSMIC",
        "supported": True,
        "connector": target_connector,
        "width": w_px,
        "height": h_px,
        "scale": scale,
        "physical_dpi": phys_dpi,
        "ideal_xwayland_policy": "Optimize for gaming and full-screen apps (descale_xwayland=fractional)" if scale > 1.0 else "Native (no scaling)",
        "target_wine_dpi": target_dpi,
        "target_xwayland_factor": 1,
        "rec_formula": rec_formula
    }

def query_x11():
    out = run_cmd("xrandr --current")
    if not out:
        return None
        
    connector = ""
    w_px = 0
    h_px = 0
    
    # 1. Look for the primary connected output first
    lines = out.split("\n")
    for line in lines:
        if " connected " in line and "primary" in line:
            parts = line.split()
            connector = parts[0]
            for p in parts:
                if "x" in p and "+" in p:
                    res_match = re.match(r'(\d+)x(\d+)\+', p)
                    if res_match:
                        w_px = int(res_match.group(1))
                        h_px = int(res_match.group(2))
                        break
            break
            
    # 2. Fall back to any connected output if no primary is specified
    if not connector or w_px == 0:
        for line in lines:
            if " connected " in line:
                parts = line.split()
                connector = parts[0]
                for p in parts:
                    if "x" in p and "+" in p:
                        res_match = re.match(r'(\d+)x(\d+)\+', p)
                        if res_match:
                            w_px = int(res_match.group(1))
                            h_px = int(res_match.group(2))
                            break
                if w_px > 0:
                    break
                    
    if w_px == 0:
        return None
        
    phys_dpi = get_edid_dpi(connector, w_px, h_px)
    return {
        "de": "Generic",
        "supported": False,
        "connector": connector,
        "width": w_px,
        "height": h_px,
        "scale": 1.0,
        "physical_dpi": phys_dpi,
        "ideal_xwayland_policy": "N/A (Native X11 Session)",
        "target_wine_dpi": 96,
        "target_xwayland_factor": 1,
        "rec_formula": "Manual Configuration Required (X11 auto-scaling unsupported)"
    }

def main():
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    de_env = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
    
    if "GNOME" in de_env:
        de_name = "GNOME"
    elif "KDE" in de_env:
        de_name = "KDE"
    elif "COSMIC" in de_env:
        de_name = "COSMIC"
    elif "CINNAMON" in de_env:
        de_name = "Cinnamon"
    else:
        de_name = de_env if de_env else "Generic"
        
    result = None
    if session_type == "x11":
        result = query_x11()
    else:
        if de_name == "GNOME":
            result = query_gnome()
        elif de_name == "KDE":
            result = query_kde()
        elif de_name == "COSMIC":
            result = query_cosmic()
            
    if not result:
        # Fallback to query_x11 if Wayland check failed or unsupported DE
        result = query_x11()
        
    if not result:
        # Fallback or unsupported
        result = {
            "de": de_name,
            "supported": False
        }
    else:
        result["de"] = de_name
        
    print(json.dumps(result))

if __name__ == "__main__":
    main()

