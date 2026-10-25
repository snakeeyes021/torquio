"""What every launcher (Dorico, Activation Manager, Download Assistant) does around starting its program."""
import os
import re
import subprocess

from .. import config, graphics, paths, prefix, run

APPS_RUNNING = re.compile(r"Dorico.*\.exe|Download.*Assistant.*\.exe|Activation.*Manager.*\.exe|aria2c", re.I)
XSET = ("xset r rate 500 30 && for keycode in {10..21} 23 {24..35} 36 {38..49} 51 {52..61} 65; do "
        "xset -r $keycode; done")
CHANGE_TITLE = "Torquio Graphics Change"
CHANGE_TEXT = ("Torquio detected a display scaling change. To apply this change, the active WINE session needs to be "
               "restarted.\\n\\nWould you like Torquio to close active applications and apply the new scaling now?")
POLICY_TITLE = "Torquio Graphics Management"
POLICY_TEXT = ("You've configured Torquio to automatically handle graphics/scaling changes. Torquio is about to adjust "
               "your global XWayland scaling policy for optimal Dorico performance.\\n\\nReminder: This is a persistent "
               "system setting change and may affect the scaling of other running XWayland applications. Your current "
               "settings will be backed up first so they can be easily restored later.\\n\\nProceed with applying this change?")


class Declined(Exception):
    """The user declined the XWayland policy change; the launcher stops (exit code 1)."""


def wine_dpi():
    """The prefix's LogPixels as Wine reports it (what the Bash launchers' reg query pipeline printed)."""
    out = run.capture(["distrobox", "enter", paths.container_name(), "--", "bash", "-c",
                       prefix.env_script() + 'wine reg query "HKCU\\Control Panel\\Desktop" /v LogPixels 2>/dev/null'],
                      stdin=None)[1]
    values = re.findall(r"0x[0-9a-fA-F]*", out)
    try:
        return "".join(str(int(v, 16)) for v in values) if values else "0"
    except ValueError:
        return "96"


def apps_running():
    out = run.capture(["distrobox", "enter", paths.container_name(), "--", "bash", "-c", "ps auxww"], stdin=None,
                      stderr=None)[1]
    return any(APPS_RUNNING.search(line) and "grep" not in line for line in out.splitlines())


def question(text, title, width=None):
    """A yes/no dialog (zenity, else kdialog); None when neither is installed."""
    if run.have("zenity"):
        cmd = ["zenity", "--question", f"--title={title}", f"--text={text}"] + ([f"--width={width}"] if width else [])
        return run.interactive(cmd, stderr=run.DEVNULL if width else None) == 0
    if run.have("kdialog"):
        return run.interactive(["kdialog", "--yesno", text, "--title", title],
                               stderr=run.DEVNULL if width else None) == 0
    return None


def kde_policy_strict():
    """graphics.kde_xwayland_policy(), stopping like the Bash launcher (set -e) when kreadconfig fails."""
    tool = graphics.kde_tool("read")
    for key in ("XwaylandClientsScale", "XwaylandClientScale"):
        code, out = run.capture([tool, "--file", "kdeglobals", "--group", "KScreen", "--key", key])
        run.check(code, True)
        if out.rstrip("\n"):
            return out.rstrip("\n")
    return ""


def manage_graphics(restartable):
    """Before a launch, in Automated Mode: bring the Wine DPI and the desktop's XWayland policy in line with the
    current monitor. `restartable`: Wine may be restarted to apply a change (not when opening a file or a
    sign-in link). Raises Declined when the user refuses the policy change."""
    if os.environ.get("XDG_SESSION_TYPE", "") == "x11" or config.get_text("manage_graphics", "false") != "true":
        return
    code, data = graphics.query_status(show_errors=True)
    run.check(code, True)
    if not graphics.supported(data):
        # As in Bash, where SUPPORTED=$(... | grep ...) failing stopped the launcher (set -e)
        raise SystemExit(1)
    de = graphics.field(data, "de", "string")
    target_dpi = graphics.field(data, "target_wine_dpi", "int")
    target_factor = graphics.field(data, "target_xwayland_factor", "int")
    scale = graphics.field(data, "scale", "number")
    freetype = config.get_text("freetype_interpreter", "40")
    dpi = config.get_text("manual_dpi", "96")
    if target_dpi and graphics.is_int(target_dpi) and int(target_dpi) > 0:
        dpi = target_dpi
    warn_dismissed = config.get_text("warn_xwayland_change", "false")

    host_change, desired, current = False, "", ""
    if de == "GNOME":
        current = graphics.xwayland_scaling_factor()
        desired = target_factor
        if graphics.is_int(target_factor) and int(target_factor) > 1 and current in ("0", ""):
            desired = current
        if desired == "1" and current in ("0", "") and (graphics.unscaled(scale) or not scale):
            desired = current
        host_change = bool(desired) and current != desired
    elif de == "KDE":
        current = kde_policy_strict() or "true"
        host_change = current != "true"
    elif de == "COSMIC":
        # As in Bash, where CURRENT_POLICY=$(cat ...) failing stopped the launcher (set -e)
        if not os.path.isfile(graphics.cosmic_policy_file()):
            raise SystemExit(1)
        current = graphics.cosmic_xwayland_policy()
        desired = current if graphics.unscaled(scale) else "fractional"
        host_change = current != desired

    wine_change = wine_dpi() != dpi
    if not (host_change or wine_change):
        return
    apply = True
    if apps_running():
        if restartable:
            answer = question(CHANGE_TEXT, CHANGE_TITLE, width=400)
            apply = True if answer is None else answer
        else:
            apply = False
    if not apply:
        return
    if host_change:
        if warn_dismissed != "true":
            if question(POLICY_TEXT, POLICY_TITLE) is False:
                raise Declined()
            config.set_text("warn_xwayland_change", "true")
        if de == "GNOME":
            if not config.get_text("original_scale_factor", ""):
                config.set_text("original_scale_factor", current or "0")
            graphics.set_gnome_xwayland_factor(desired)
        elif de == "KDE":
            if not config.get_text("original_kde_policy", ""):
                config.set_text("original_kde_policy", current or "false")
            graphics.set_kde_xwayland_policy("true")
        elif de == "COSMIC":
            if not config.get_text("original_cosmic_policy", ""):
                config.set_text("original_cosmic_policy", current or "none")
            graphics.write_cosmic_policy(desired)
    if wine_change:
        prefix.set_dpi(dpi, freetype)
    prefix.restart_wineserver()


def fix_key_repeat():
    """Turn off auto-repeat for character keys (prone to runaway repeats under XWayland), keep it for
    navigation and editing keys."""
    run.interactive(["distrobox", "enter", paths.container_name(), "--", "bash", "-c", XSET],
                    stdout=run.DEVNULL, stderr=run.DEVNULL)


def write_runner(name, text):
    """~/.local/share/torquio/NAME, executable."""
    path = os.path.join(paths.home(), ".local/share/torquio", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    umask = os.umask(0)
    os.umask(umask)
    os.chmod(path, os.stat(path).st_mode | (0o111 & ~umask))
    return path


def handover(name, value):
    """The file a runner reads its argument from (a file to open, a sign-in link); removed without one."""
    path = os.path.join(paths.home(), ".local/share/torquio", name)
    if value:
        with open(path, "w") as f:
            f.write(value + "\n")
    else:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def runner_text(template, values):
    """A runner script from scripts/templates/TEMPLATE, with @NAME@ replaced by values[NAME]."""
    with open(os.path.join(paths.repo_dir(), "scripts/templates", template)) as f:
        text = f.read()
    for name, value in values.items():
        text = text.replace(f"@{name}@", value)
    return text


def run_in_container(runner):
    return run.interactive(["distrobox", "enter", paths.container_name(), "--", runner])


def report_crashes():
    """Print and remove the crash reports Torquio's debugger helper left in the prefix."""
    import glob
    for crash_log in sorted(glob.glob(os.path.join(glob.escape(paths.prefix_dir()), "drive_c", "winedbg_crash_*.log"))):
        if not os.path.isfile(crash_log):
            continue
        print()
        print("=========================================")
        print("=== PROCESS CRASH DETECTED ===")
        print(f"Crash Details Log: {os.path.basename(crash_log)}")
        print(f"Time: {subprocess.run(['date'], stdout=subprocess.PIPE, text=True).stdout.rstrip()}")
        print("-----------------------------------------")
        with open(crash_log, "rb") as f:
            os.write(1, f.read())
        print("=========================================")
        os.remove(crash_log)
