"""The graphics status screen at the top of Configure Graphics & Scaling (`torquio --graphics`)."""
from .. import config, graphics
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
