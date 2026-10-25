"""The graphics status screen at the top of Configure Graphics & Scaling (`torquio --graphics`)."""
from .. import config, graphics, prefix, ui
from ..ui import BLUE, DARK_GRAY, GRAY, GREEN, RED, RESET, WINE, YELLOW, echo
from .status import on, session_type


def show_diagnostics(graphics_json, de, supported, w_px, h_px):
    """show_graphics_diagnostics, given the JSON and the values configure_graphics already read from it."""
    x11 = session_type() == "x11"
    cur_manage = config.get_text("manage_graphics", "false")
    ft_int = config.get_text("freetype_interpreter", "40")
    mode = "N/A (Wayland Only)" if x11 else ("Automated Mode" if on(cur_manage) else "Manual Mode")
    match = "N/A (Wayland Only)" if x11 else ("On" if on(config.get_text("match_physical_dpi", "false")) else "Off")

    echo(f"{BLUE}=== Torquio Graphics Status & Diagnostics ==={RESET}")
    echo()

    connector = graphics.field(graphics_json, "connector", "string")
    scale = graphics.field(graphics_json, "scale", "number")
    target_dpi = graphics.field(graphics_json, "target_wine_dpi", "int")

    if not w_px or (graphics.is_int(w_px) and int(w_px) == 0):
        echo(f"  Active Main Monitor:       {RED}Unknown / Undetected{RESET}")
        echo(f"  Desktop Scale Factor:      {RED}Unknown / Undetected{RESET}")
    else:
        echo(f"  Active Main Monitor:       {WINE}{w_px}x{h_px}{RESET} ({connector or 'Unknown'})")
        echo(f"  Desktop Scale Factor:      {WINE}{graphics.scale_percent(scale)}% ({scale}){RESET}")
    echo()

    echo(f"  {BLUE}[Current System Values]{RESET}")
    sys_policy, effective, rec_policy = graphics.policies(de, scale, session_type())
    echo(f"  - Graphics Management:         {WINE}{mode}{RESET}")
    echo(f"  - Match Physical DPI:          {WINE}{match}{RESET}")
    echo(f"  - XWayland Policy Setting:     {WINE}{sys_policy}{RESET}")
    echo(f"  - Effective XWayland Scaling:  {WINE}{effective}{RESET}")
    echo(f"  - Wine Prefix DPI:             {WINE}{graphics.wine_prefix_dpi()} DPI{RESET}")
    echo(f"  - FreeType Interpreter:        {WINE}v{ft_int}{RESET}")
    echo()

    echo(f"  {BLUE}[Torquio Recommendations for this Monitor]{RESET}")
    if x11:
        echo(f"  - Recommended Scaling Policy:  {YELLOW}N/A (Native X11 Session){RESET}")
        echo(f"  - Recommended Wine DPI:        {YELLOW}Manual Configuration Required{RESET}")
        echo()
        echo(f"  {YELLOW}[X11 Scaling Notice]{RESET}")
        echo("  The proper scaling settings will differ for the various X11 desktop environments.")
        echo("  Please consult your own particular DE's scaling method and set the Wine Prefix")
        echo("  DPI manually using option 2 if needed.")
        echo()
        echo("  As an example, on Mint, you would set the following DPI values depending on")
        echo("  what desktop scaling you have enabled in your settings:")
        echo(f"  - {WINE}Integer Scaling (e.g., 200%){RESET}: Set DPI to Scale × 96 (e.g., 192 DPI).")
        echo(f"  - {WINE}Fractional Scaling with 'Scale Down' enabled{RESET}: Set DPI to 192 DPI.")
        echo(f"  - {WINE}Fractional Scaling with 'Scale Up' enabled{RESET}: Leave DPI on default 96 DPI.")
    elif supported:
        rec_formula = graphics.field(graphics_json, "rec_formula", "string")
        echo(f"  - Recommended XWayland Policy: {GREEN}{rec_policy}{RESET}")
        echo(f"  - Recommended Wine DPI:        {GREEN}{target_dpi or '96'} DPI{RESET} ({rec_formula})")
    else:
        echo(f"  - Recommended XWayland Policy: {RED}Unsupported DE (Manual management required){RESET}")
        echo(f"  - Recommended Wine DPI:        {RED}Unsupported DE (Manual management required){RESET}")
    echo()

    if not x11:
        if on(cur_manage):
            echo(f"  {GREEN}Torquio is automatically managing these settings.{RESET}")
        else:
            echo(f"  {DARK_GRAY}To let Torquio handle this automatically, switch to Automated Mode.{RESET}")
        echo()

    wide = w_px and graphics.is_int(w_px) and int(w_px) >= 3840
    tall = h_px and graphics.is_int(h_px) and int(h_px) >= 2160
    if w_px and h_px and (wide or tall):
        echo(f"  {YELLOW}[!] Performance Warning: At 4K+ resolutions, we have noticed some performance{RESET}")
        echo(f"      {YELLOW}degradation/lagginess even on decent hardware. If you experience unacceptable{RESET}")
        echo(f"      {YELLOW}lag, consider manually bumping your system desktop resolution down to 1440p or{RESET}")
        echo(f"      {YELLOW}1080p before you launch Dorico.{RESET}")
        echo()

    echo(f"{GRAY}================================================================{RESET}")
    echo()


def restore_policy_banner(de, from_desc, to_desc):
    echo()
    echo(f"{BLUE}================================================================{RESET}")
    echo(f"          {WINE}XWayland Global Scaling Policy Restore{RESET}")
    echo(f"{BLUE}================================================================{RESET}")
    echo(f"Torquio detected that host {de} XWayland policy was modified from {WINE}{from_desc}{RESET} to {WINE}{to_desc}{RESET}.")
    echo("During setup/launch, you set Torquio to automatically adjust your desktop")
    echo("environment's global XWayland scaling policy to match the ideal")
    echo("setting for Dorico.")
    echo()
    echo("Restoring this setting will return your system to its original scaling")
    echo("behavior (which may affect how other XWayland applications scale).")
    echo(f"{BLUE}================================================================{RESET}")
    echo()


def gnome_desc(value):
    if value == "1":
        return "Framebuffer Upscale (xwayland-scaling-factor=1)"
    if value in ("0", ""):
        return "System Default (xwayland-scaling-factor=0)"
    return f"Override Scaling (xwayland-scaling-factor={value})"


def kde_desc(value):
    if value == "false":
        return "Scale XWayland clients by compositor (XwaylandClientsScale=false)"
    return "Scale XWayland clients themselves (XwaylandClientsScale=true)"


def cosmic_desc(value):
    if value == "fractional":
        return "Optimize for gaming and full-screen apps (descale_xwayland=fractional)"
    if value == "true":
        return "Optimize for applications (descale_xwayland=true)"
    return "Maximum compatibility mode (descale_xwayland=false)"


def offer_restore(de):
    """After switching to Manual Mode: offer to put back the desktop's XWayland policy Automated Mode changed."""
    orig_scale = config.get_text("original_scale_factor", "")
    orig_kde = config.get_text("original_kde_policy", "")
    orig_cosmic = config.get_text("original_cosmic_policy", "")
    question = "Would you like to restore your {} XWayland scale setting back to its original value ({})? [Y/n]: "
    if de == "GNOME" and orig_scale:
        current = graphics.xwayland_scaling_factor()
        if (current or "0") != orig_scale:
            from_desc, to_desc = gnome_desc(orig_scale), gnome_desc(current)
            restore_policy_banner("GNOME", from_desc, to_desc)
            if not ui.no(ui.ask(question.format("GNOME", from_desc))):
                graphics.set_gnome_xwayland_factor(orig_scale)
                echo(f"GNOME XWayland scale setting restored to {from_desc}.")
    elif de == "KDE" and orig_kde:
        current = graphics.kde_xwayland_policy() or "true"
        if current != orig_kde:
            from_desc, to_desc = kde_desc(orig_kde), kde_desc(current)
            restore_policy_banner("KDE", from_desc, to_desc)
            if not ui.no(ui.ask(question.format("KDE", from_desc))):
                graphics.set_kde_xwayland_policy(orig_kde)
                echo(f"KDE XWayland scale setting restored to {from_desc}.")
    elif de == "COSMIC" and orig_cosmic:
        current = graphics.cosmic_xwayland_policy() or "none"
        if current != orig_cosmic:
            from_desc, to_desc = cosmic_desc(orig_cosmic), cosmic_desc(current)
            restore_policy_banner("COSMIC", from_desc, to_desc)
            if not ui.no(ui.ask(question.format("COSMIC", from_desc))):
                graphics.write_cosmic_policy(None if orig_cosmic == "none" else orig_cosmic)
                echo(f"COSMIC XWayland scale setting restored to {from_desc}.")
    for key in ("original_scale_factor", "original_kde_policy", "original_cosmic_policy"):
        config.set_text(key, "")


AUTOMATED_WARNING = [
    f"{YELLOW}================================================================{RESET}",
    f"{YELLOW}WARNING: Enabling Automated Mode will change your desktop's{RESET}",
    f"{YELLOW}global XWayland scaling policy to match the ideal policy for Dorico.{RESET}",
    f"{YELLOW}This is a persistent system setting change (not temporary) and may{RESET}",
    f"{YELLOW}affect the size/rendering of other XWayland applications going forward.{RESET}",
    f"{YELLOW}You may also want to restart any currently running XWayland applications{RESET}",
    f"{YELLOW}after enabling this mode.{RESET}",
    f"{YELLOW}----------------------------------------------------------------{RESET}",
    f"{GREEN}Torquio will back up your current desktop scaling settings,{RESET}",
    f"{GREEN}and you can easily restore them at any time by switching{RESET}",
    f"{GREEN}back to Manual Mode.{RESET}",
    f"{YELLOW}================================================================{RESET}",
]


def toggle_management(cur_manage, supported, de):
    """Option 1. Returns True to show the screen again."""
    if session_type() == "x11":
        echo(f"{RED}Error: Automated Graphics Management is a Wayland-Only feature.{RESET}")
        echo("The proper scaling settings will differ across X11 desktop environments.")
        echo("Please consult your DE's scaling method and set WINE Prefix DPI manually using option 2.")
        echo()
        ui.pause()
        return True
    if not supported:
        echo("Automated XWayland Management is not supported on your Desktop Environment. Please see the "
             "recommendations in the graphics configuration page to assist in manually managing your display "
             "and scaling settings.")
        echo()
        ui.pause()
        return True
    if on(cur_manage):
        if not ui.yes(ui.ask("Switching to Manual Mode will disable automated launch-time scaling overrides. Continue? [y/N]: ")):
            echo("Switch to Manual Mode cancelled.")
            ui.pause()
            return True
        config.set_text("manage_graphics", "false")
        echo("Switched to Manual Mode.")
        offer_restore(de)
        ui.pause()
    else:
        for line in AUTOMATED_WARNING:
            echo(line)
        echo()
        if not ui.yes(ui.ask("Do you want to enable Automated Mode? [y/N]: ")):
            echo("Switch to Automated Mode cancelled.")
            ui.pause()
            return True
        config.set_text("manage_graphics", "true")
        echo("Switched to Automated Management Mode.")
    graphics.apply_settings(echo)
    return True


def set_prefix_dpi(cur_interpreter):
    """Option "Set/change WINE Prefix DPI" (Manual Mode)."""
    echo("Standard default DPI is 96.")
    new_dpi = ui.ask("Enter DPI value to inject into prefix (e.g. 96, 120, 144, 192): ")
    if not new_dpi.isascii() or not new_dpi.isdigit():
        echo("Invalid input. DPI must be an integer.")
        ui.pause()
        return
    if graphics.wine_prefix_dpi() == new_dpi:
        echo(f"DPI of the Wine prefix is already set to {new_dpi}. No changes made.")
        ui.pause()
        return
    echo()
    echo(f"{YELLOW}================================================================{RESET}")
    echo(f"{YELLOW}WARNING: Changing the prefix DPI requires restarting the Wine server.{RESET}")
    echo(f"{YELLOW}This will immediately close any active Dorico, SAM, or Steinberg windows.{RESET}")
    echo(f"{YELLOW}Please save your work first.{RESET}")
    echo(f"{YELLOW}================================================================{RESET}")
    echo()
    if not ui.yes(ui.ask(f"Do you want to continue applying {new_dpi} DPI? [y/N]: ")):
        echo("DPI change cancelled.")
        ui.pause()
        return
    echo(f"Applying {new_dpi} DPI value to Wine prefix...")
    prefix.set_dpi(new_dpi, cur_interpreter)
    echo("Restarting Wine server to load changes...")
    prefix.restart_wineserver()
    echo("DPI injection successful.")
    ui.pause()


def choose_interpreter():
    echo()
    echo(f"{BLUE}=== FreeType Hinting Interpreter Selection ==={RESET}")
    echo(f"  {WINE}1){RESET} v40 (Thicker/bolder, but some fonts can look smudgey) [Default]")
    echo(f"  {WINE}2){RESET} v35 (Thinner/crisper, but some fonts can look anemic)")
    echo(f"  {WINE}3){RESET} [Back to graphics menu]")
    echo()
    choice = ui.ask("Select interpreter style (1-3): ")
    if choice in ("1", "2"):
        version = "40" if choice == "1" else "35"
        config.set_text("freetype_interpreter", version)
        echo(f"FreeType Hinting Interpreter set to v{version}!")
        graphics.apply_settings(echo)
        echo()
        ui.pause()


def toggle_match_physical(cur_manage):
    ui.clear()
    match = "On" if on(config.get_text("match_physical_dpi", "false")) else "Off"
    echo(f"{BLUE}================================================================{RESET}")
    echo(f"          {WINE}Match Hardware Physical DPI{RESET}")
    echo(f"{BLUE}================================================================{RESET}")
    echo()
    echo("By default, Torquio uses a standard 96 DPI logical baseline as")
    echo("the anchor for scaling calculations. This mirrors standard OS")
    echo("scaling, where logical DPI scales linearly (e.g. 150% = 144 DPI).")
    echo()
    echo("Alternatively, you can choose to match your monitor's exact")
    echo("hardware physical DPI (e.g. 161 DPI). This may be desirable if")
    echo("you prefer a slightly different scale in Dorico to compensate for")
    echo("the physical size of your screen.")
    echo()
    echo(f"Currently, Match Hardware Physical DPI is: {WINE}{match}{RESET}")
    echo(f"{BLUE}================================================================{RESET}")
    echo()
    enable = match == "Off"
    verb = "enable" if enable else "disable"
    if ui.yes(ui.ask(f"Do you want to {verb} matching hardware physical DPI? [y/N]: ")):
        config.set_text("match_physical_dpi", "true" if enable else "false")
        echo(f"Match Hardware Physical DPI {verb}d.")
        if on(cur_manage):
            graphics.apply_settings(echo)
    else:
        echo("No changes made.")
    ui.pause()


def configure():
    """Configure Graphics & Scaling (main menu, `torquio --graphics`)."""
    while True:
        cur_manage = config.get_text("manage_graphics", "false")
        cur_interpreter = config.get_text("freetype_interpreter", "40")
        data = graphics.query()
        de = graphics.field(data, "de", "string")
        supported = graphics.supported(data)
        w_px = graphics.field(data, "width", "int")
        h_px = graphics.field(data, "height", "int")
        show_diagnostics(data, de, '"supported": true' if supported else "", w_px, h_px)

        echo("Options:")
        count = 1
        echo(f"  {WINE}{count}){RESET} Auto Manage Graphics")
        opt_manage = count
        opt_dpi = 0
        if cur_manage.lower() not in ("true", "1"):
            count += 1
            echo(f"  {WINE}{count}){RESET} Set/change WINE Prefix DPI")
            opt_dpi = count
        count += 1
        echo(f"  {WINE}{count}){RESET} FreeType Hinting Interpreter")
        opt_interpreter = count
        opt_match = 0
        if session_type() != "x11":
            count += 1
            echo(f"  {WINE}{count}){RESET} Match Hardware Physical DPI")
            opt_match = count
        count += 1
        echo(f"  {WINE}{count}){RESET} [Back to main menu]")
        echo("")

        opt = ui.ask(f"Select an option to toggle/change (1-{count}): ")
        if opt == str(opt_manage):
            toggle_management(cur_manage, supported, de)
        elif opt_dpi > 0 and opt == str(opt_dpi):
            set_prefix_dpi(cur_interpreter)
        elif opt == str(opt_interpreter):
            choose_interpreter()
        elif opt == str(opt_match):
            toggle_match_physical(cur_manage)
        else:
            return
