"""Display and scaling facts for the dashboard and the graphics screen.

The live monitor query is still scripts/3-runtime_handlers/torquio_graphics.py (the launchers in
~/.local/bin use a copy of it; it moves here with them in stage 6 of the port).
"""
import ast
import os
import re
import sys

from . import paths, run

GRAPHICS_SCRIPT = "scripts/3-runtime_handlers/torquio_graphics.py"


def query():
    """torquio_graphics.py's JSON, as text ("" if it fails)."""
    return run.capture([sys.executable, os.path.join(paths.repo_dir(), GRAPHICS_SCRIPT)])[1].rstrip("\n")


def field(graphics_json, key, kind):
    """A value from the JSON, read the way the Bash screens did (grep -o, then cut): `kind` is "string",
    "int" (digits) or "number" (digits and dots). Every match, one per line; "" if there's none."""
    pattern = {"string": r'"%s": "([^"]*)', "int": r'"%s": ([0-9]*)', "number": r'"%s": ([0-9.]*)'}[kind]
    return "\n".join(re.findall(pattern % re.escape(key), graphics_json))


def supported(graphics_json):
    return '"supported": true' in graphics_json


def scale_percent(scale):
    """`python3 -c "print(int(round($scale * 100)))" || echo 100`"""
    try:
        return str(int(round(ast.literal_eval(scale) * 100)))
    except Exception:
        return "100"


def is_int(text):
    """Whether Bash's [ "$text" -gt 0 ] can compare it (otherwise the test fails)."""
    return bool(re.fullmatch(r"\s*[+-]?[0-9]+\s*", text))


def xwayland_scaling_factor():
    """GNOME's xwayland-scaling-factor as digits ("" if unset or not GNOME), as get_xwayland_scaling_factor."""
    def last_fields(schema):
        out = run.capture(["gsettings", "get", schema, "xwayland-scaling-factor"])[1]
        return "\n".join((line.split() or [""])[-1] for line in out.splitlines()).rstrip("\n")
    value = last_fields("org.gnome.mutter.wayland") or last_fields("org.gnome.mutter")
    lines = [line.replace(" ", "").split(".")[0] for line in value.split("\n")]
    return "".join(c for c in "\n".join(lines) if c in "0123456789")


def kde_xwayland_policy():
    """KScreen's XwaylandClientsScale setting ("" if unset)."""
    tool = "kreadconfig6" if run.have("kreadconfig6") else "kreadconfig5"
    for key in ("XwaylandClientsScale", "XwaylandClientScale"):
        value = run.capture([tool, "--file", "kdeglobals", "--group", "KScreen", "--key", key])[1].rstrip("\n")
        if value:
            return value
    return ""


def cosmic_xwayland_policy():
    try:
        with open(os.path.join(paths.home(), ".config/cosmic/com.system76.CosmicComp/v1/descale_xwayland")) as f:
            return f.read().rstrip("\n")
    except (OSError, UnicodeDecodeError):
        return ""


def policies(de, scale, session_type):
    """(configured XWayland policy, effective scaling, recommended policy) for the screens."""
    is_scaled = scale not in ("1", "1.0", "1.00", "")
    if re.search("X11", de) or session_type == "x11":
        sys_policy = rec_policy = "N/A (Native X11 Session)"
        is_scaled = False
    elif de == "GNOME":
        gp = xwayland_scaling_factor()
        if gp == "1":
            sys_policy = "[GNOME] Framebuffer Upscale (xwayland-scaling-factor=1)"
        elif gp in ("0", ""):
            sys_policy = "[GNOME] System Default (Supersampled Downscale)"
        else:
            sys_policy = f"[GNOME] Native Integer Scaling (xwayland-scaling-factor={gp})"
        if scale in ("2", "2.0", "3", "3.0"):
            rec_policy = f"[GNOME] Native Integer Scaling (xwayland-scaling-factor={round(float(scale))})"
        else:
            rec_policy = "[GNOME] Framebuffer Upscale (xwayland-scaling-factor=1)"
    elif de == "KDE":
        kp = kde_xwayland_policy()
        if kp in ("true", ""):
            sys_policy = "[KDE] Scale XWayland clients themselves"
        else:
            sys_policy = "[KDE] Scale XWayland clients by compositor"
        rec_policy = "[KDE] Scale XWayland clients themselves"
    elif de == "COSMIC":
        cp = cosmic_xwayland_policy()
        if cp == "fractional":
            sys_policy = "[COSMIC] Optimize for gaming and full-screen apps"
        elif cp == "true":
            sys_policy = "[COSMIC] Optimize for applications"
        else:
            sys_policy = "[COSMIC] System Default (Maximum compatibility)"
        rec_policy = "[COSMIC] Optimize for gaming and full-screen apps"
    else:
        sys_policy = f"Unsupported DE ({de or 'Unknown'})"
        rec_policy = "Unsupported DE (Manual management required)"
    if not is_scaled:
        return sys_policy, "Native (no scaling)", "Native (no scaling)"
    return sys_policy, sys_policy, rec_policy


def wine_prefix_dpi():
    """The prefix's LogPixels (96 if unset), or "Unknown" without a prefix."""
    reg_file = os.path.join(paths.prefix_dir(), "user.reg")
    try:
        with open(reg_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return "Unknown"
    match = re.search(r"\[Control Panel\\\\Desktop\][^\[]*?\"LogPixels\"=dword:([0-9a-fA-F]+)", content)
    return str(int(match.group(1), 16)) if match else "96"
