"""Display and scaling facts for the dashboard and the graphics screen.

The live monitor query is still scripts/3-runtime_handlers/torquio_graphics.py (the launchers in
~/.local/bin use a copy of it; it moves here with them in stage 6 of the port).
"""
import ast
import os
import re
import sys

from . import config, container, paths, prefix, run

GRAPHICS_SCRIPT = "scripts/3-runtime_handlers/torquio_graphics.py"


def query(show_errors=False):
    """torquio_graphics.py's JSON, as text ("" if it fails)."""
    return run.capture([sys.executable, os.path.join(paths.repo_dir(), GRAPHICS_SCRIPT)],
                       stderr=None if show_errors else run.DEVNULL)[1].rstrip("\n")


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
    tool = kde_tool("read")
    for key in ("XwaylandClientsScale", "XwaylandClientScale"):
        value = run.capture([tool, "--file", "kdeglobals", "--group", "KScreen", "--key", key])[1].rstrip("\n")
        if value:
            return value
    return ""


COSMIC_POLICY = ".config/cosmic/com.system76.CosmicComp/v1/descale_xwayland"


def cosmic_policy_file():
    return os.path.join(paths.home(), COSMIC_POLICY)


def cosmic_xwayland_policy():
    try:
        with open(cosmic_policy_file()) as f:
            return f.read().rstrip("\n")
    except (OSError, UnicodeDecodeError):
        return ""


def write_cosmic_policy(value):
    """echo VALUE > descale_xwayland (None removes the file, which means COSMIC's default)."""
    os.makedirs(os.path.dirname(cosmic_policy_file()), exist_ok=True)
    try:
        if value is None:
            os.remove(cosmic_policy_file())
        else:
            with open(cosmic_policy_file(), "w") as f:
                f.write(value + "\n")
    except OSError:
        pass


def kde_tool(kind):
    """kreadconfig6/kwriteconfig6, or the Plasma 5 tool when there's no 6."""
    return f"k{kind}config6" if run.have(f"k{kind}config6") else f"k{kind}config5"


def set_kde_xwayland_policy(value):
    tool = kde_tool("write")
    for key in ("XwaylandClientsScale", "XwaylandClientScale"):
        run.interactive([tool, "--file", "kdeglobals", "--group", "KScreen", "--key", key, value], stderr=run.DEVNULL)
    run.interactive(["dbus-send", "--session", "--dest=org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure"],
                    stderr=run.DEVNULL)


def set_gnome_xwayland_factor(value):
    schemas = run.capture(["gsettings", "list-schemas"], stderr=None)[1]
    schema = "org.gnome.mutter.wayland" if "org.gnome.mutter.wayland" in schemas else "org.gnome.mutter"
    run.interactive(["gsettings", "set", schema, "xwayland-scaling-factor", value], stderr=run.DEVNULL)


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


def unscaled(scale):
    return scale in ("1", "1.0", "1.00")


def apply_settings(say):
    """apply_graphics_settings: write the Wine DPI (and, in Automated Mode, the desktop's XWayland policy) and
    restart the Wine server. `say` shows progress messages. Does nothing without a container and prefix."""
    if not container.exists() or not os.path.isdir(paths.prefix_dir()):
        return
    say("Applying graphics settings to Wine prefix...")
    manage = config.get_text("manage_graphics", "false")
    if os.environ.get("XDG_SESSION_TYPE", "") == "x11":
        manage = "false"
    dpi = config.get_text("manual_dpi", "96")
    freetype = config.get_text("freetype_interpreter", "40")

    if manage == "true":
        data = query(show_errors=True)
        target_dpi = field(data, "target_wine_dpi", "int")
        target_factor = field(data, "target_xwayland_factor", "int")
        de = field(data, "de", "string")
        scale = field(data, "scale", "number")
        if target_dpi and is_int(target_dpi) and int(target_dpi) > 0:
            dpi = target_dpi
        prefix.set_dpi(dpi, freetype)

        if de == "GNOME":
            current = xwayland_scaling_factor()
            desired = target_factor
            if is_int(target_factor) and int(target_factor) > 1 and current in ("0", ""):
                desired = current
            if desired == "1" and current in ("0", "") and (unscaled(scale) or not scale):
                desired = current
            if desired and current != desired:
                if not config.get_text("original_scale_factor", ""):
                    config.set_text("original_scale_factor", current or "0")
                    say(f"Backed up current GNOME XWayland scaling policy ({current or '0'}).")
                set_gnome_xwayland_factor(desired)
        elif de == "KDE":
            current = kde_xwayland_policy() or "true"
            if current != "true":
                if not config.get_text("original_kde_policy", ""):
                    config.set_text("original_kde_policy", current)
                    say(f"Backed up current KDE XWayland scaling policy ({current}).")
                set_kde_xwayland_policy("true")
        elif de == "COSMIC":
            current = cosmic_xwayland_policy()
            desired = current if unscaled(scale) else "fractional"
            if current != desired:
                if not config.get_text("original_cosmic_policy", ""):
                    config.set_text("original_cosmic_policy", current or "none")
                    say(f"Backed up current COSMIC XWayland scaling policy ({current or 'none'}).")
                write_cosmic_policy(desired)
        config.set_text("warn_xwayland_change", "true")

    prefix.set_focus_options()
    say("Restarting Wine server to load changes...")
    prefix.restart_wineserver()
    say("Graphics settings successfully applied.")
