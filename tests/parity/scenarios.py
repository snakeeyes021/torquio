"""Flows the parity harness compares. Each scenario:
    name           short identifier (run.py takes names to run a subset)
    args           arguments to ./torquio
    input          what the user types (all at once; echo is off, so it doesn't appear in the output)
    files          {path relative to $HOME: contents} created before the run
    compare_files  paths relative to $HOME whose contents must match afterwards
    timeout        seconds (default 120)
    env            environment variables to set (None removes one), including the FAKE_* ones below
    fakes          {program: sh script body} replacing a program for this scenario
    repo_files     {path in the repo: contents} swapped in for this scenario (both copies)

The fake container (harness.py) is set up by environment variables:
    FAKE_CONTAINER        its name in `distrobox list` (unset: there is no container)
    FAKE_STATUS           its STATUS column (default "Up 2 hours")
    FAKE_IMAGE            what `podman container inspect` reports; "current" = this copy's prebuilt image
    FAKE_MACHINE_ID       its /var/lib/dbus/machine-id; "derived" = the one derived from this computer's
    FAKE_BUILD_INFO       its engine build record (printf %b); "matching" = what this copy would build
    FAKE_PROBE            the dashboard's GPU probe output (printf %b)
    FAKE_XWAYLAND_FACTOR  `gsettings get ... xwayland-scaling-factor` output (unset: gsettings fails)
    FAKE_KDE_POLICY       kreadconfig6's answer
    FAKE_NTSYNC_MODULE    "yes": `modinfo ntsync` succeeds
"""
import json

CONFIG = ".config/torquio/config.json"
PREFIX = ".local/share/torquio/prefix"
GRAPHICS = "scripts/3-runtime_handlers/torquio_graphics.py"


def graphics(de=None, **result):
    """torquio_graphics.py replaced by one that prints this result (or fails, given nothing)."""
    if de is None:
        return {GRAPHICS: "import sys\nsys.exit(1)\n"}
    return {GRAPHICS: f"print({json.dumps(json.dumps(dict(result, de=de)))})\n"}


def config(**values):
    return {CONFIG: json.dumps(values, indent=4)}


USER_REG = 'WINE REGISTRY Version 2\n\n[Control Panel\\\\Desktop] 1700000000\n"FontSmoothing"="2"\n"LogPixels"=dword:00000078\n'
INSTALLED = {
    f"{PREFIX}/.torquio_core_installed": "",
    f"{PREFIX}/user.reg": USER_REG,
    f"{PREFIX}/drive_c/users/me/AppData/Local/Cantai/Cantai.exe": "",
}
VKD3D = {f".local/share/torquio/vkd3d-proton/{v}/x64/d3d12.dll": "" for v in ("2.9", "2.14.1", "2.13")}
PROBE_TWO_GPUS = ("gpu=PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU|Intel(R) Iris(R) Xe Graphics\\n"
                  "gpu=PHYSICAL_DEVICE_TYPE_DISCRETE_GPU|NVIDIA GeForce RTX 4060 Laptop GPU\\n"
                  "gpu=PHYSICAL_DEVICE_TYPE_CPU|llvmpipe (LLVM 19.1.1, 256 bits)\\n"
                  "nvidia=yes\\ndxcore=patched\\nvulkaninfo=yes\\n")
GNOME_125 = graphics("GNOME", supported=True, connector="eDP-1", width=2560, height=1600, scale=1.25, physical_dpi=189,
                     ideal_xwayland_policy="Framebuffer Upscale (xwayland-scaling-factor=1)", target_wine_dpi=120,
                     target_xwayland_factor=1, rec_formula="Formula: 96 x 1.25 scale")

SCENARIOS = [
    {"name": "unknown-flag", "args": ["--no-such-flag"]},
    {"name": "status", "args": ["--status"]},
    {"name": "menu-exit", "input": "7\n"},
    {"name": "menu-invalid", "input": "42\n\n7\n"},
    {"name": "menu-eof", "input": "\x04"},  # Ctrl+D at the menu prompt
    {"name": "settings-toggle", "input": "6\n1\n1\n2\n7\n", "compare_files": [CONFIG]},
    {"name": "settings-existing-config", "input": "6\n1\n2\n7\n", "compare_files": [CONFIG],
     "files": {CONFIG: '{\n    "manage_graphics": true,\n    "manual_dpi": 120,\n    "check_for_updates": false\n}'}},
    {"name": "settings-broken-config", "input": "6\n1\n2\n7\n", "compare_files": [CONFIG],
     "files": {CONFIG: "{not json"}},
    {"name": "manifest", "args": ["--manifest"]},
    {"name": "export-logs", "args": ["--export-logs"]},
    {"name": "uninstall-nothing-installed", "args": ["--uninstall"], "input": "n\n\n"},

    # Dashboard and graphics screen in different states
    {"name": "status-prebuilt-current", "args": ["--status"], "repo_files": GNOME_125,
     "files": {**INSTALLED, **VKD3D, **config(ai_gpu="auto", manage_graphics=True, freetype_interpreter=40)},
     "env": {"FAKE_CONTAINER": "torquio-env", "FAKE_IMAGE": "current", "FAKE_MACHINE_ID": "derived",
             "FAKE_PROBE": PROBE_TWO_GPUS, "FAKE_XWAYLAND_FACTOR": "uint32 1", "FAKE_NTSYNC_MODULE": "yes"}},
    {"name": "status-prebuilt-outdated-kde", "args": ["--status"],
     "repo_files": graphics("KDE", supported=True, connector="DP-2", width=3840, height=2160, scale=2.0,
                            target_wine_dpi=192, rec_formula="Formula: 96 x 2"),
     "files": {**INSTALLED, f"{PREFIX}/.torquio_core_installed": None, **config(ai_gpu="off", match_physical_dpi="True")},
     "env": {"XDG_CURRENT_DESKTOP": "KDE", "FAKE_CONTAINER": "torquio-env",
             "FAKE_IMAGE": "ghcr.io/snakeeyes021/torquio-env:build-000000000000",
             "FAKE_MACHINE_ID": "0123456789abcdef0123456789abcdef", "FAKE_PROBE": "vulkaninfo=yes\\n",
             "FAKE_KDE_POLICY": "false"}},
    {"name": "status-local-current-cosmic", "args": ["--status"],
     "repo_files": graphics("COSMIC", supported=True, connector="HDMI-A-1", width=1920, height=1080, scale=1.5,
                            target_wine_dpi=144, rec_formula="Formula: 96 x 1.5"),
     "files": {**INSTALLED, **config(ai_gpu="NVIDIA GeForce RTX 4060"),
               ".config/cosmic/com.system76.CosmicComp/v1/descale_xwayland": "fractional\n"},
     "env": {"XDG_CURRENT_DESKTOP": "COSMIC", "FAKE_CONTAINER": "torquio-env", "FAKE_IMAGE": "localhost/torquio-env:latest",
             "FAKE_BUILD_INFO": "matching", "FAKE_MACHINE_ID": "abc", "FAKE_PROBE": ""}},
    {"name": "status-local-outdated-x11", "args": ["--status"],
     "repo_files": graphics("Cinnamon", supported=True, connector="HDMI-1", width=1920, height=1080, scale=1.0,
                            target_wine_dpi=96, rec_formula="Formula: native"),
     "files": {**INSTALLED, **VKD3D, **config(manage_graphics=True, match_physical_dpi=True)},
     "env": {"XDG_SESSION_TYPE": "x11", "XDG_CURRENT_DESKTOP": "X-Cinnamon", "FAKE_CONTAINER": "torquio-env",
             "FAKE_IMAGE": "localhost/torquio-env:latest", "FAKE_BUILD_INFO": "zhiyi_commit=deadbeef\\npatch=0 old\\n",
             "FAKE_MACHINE_ID": "derived", "FAKE_PROBE": "gpu=PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU|AMD Radeon \\\\t 780M\\n"}},
    {"name": "status-local-no-record-no-graphics", "args": ["--status"], "repo_files": graphics(),
     "files": {f"{PREFIX}/user.reg": "WINE REGISTRY Version 2\n"},
     "env": {"FAKE_CONTAINER": "torquio-env", "FAKE_STATUS": "  ", "FAKE_IMAGE": "", "FAKE_BUILD_INFO": "",
             "FAKE_MACHINE_ID": "", "FAKE_PROBE": "nvidia=yes\\n"}},
    {"name": "status-unsupported-de", "args": ["--status"], "repo_files": graphics("SWAY", supported=False),
     "files": config(manage_graphics=1, freetype_interpreter=35),
     "env": {"XDG_CURRENT_DESKTOP": "sway"}},
    {"name": "status-gnome-integer", "args": ["--status"],
     "repo_files": graphics("GNOME", supported=True, connector="DP-1", width=5120, height=2880, scale=2,
                            target_wine_dpi=96, rec_formula="Formula: integer"),
     "env": {"FAKE_XWAYLAND_FACTOR": "uint32 0"}},
    {"name": "graphics-gnome-manual", "args": ["--graphics"], "input": "5\n", "repo_files": GNOME_125,
     "files": {**INSTALLED}, "env": {"FAKE_XWAYLAND_FACTOR": "uint32 2"}},
    {"name": "graphics-gnome-automated-4k", "args": ["--graphics"], "input": "4\n",
     "repo_files": graphics("GNOME", supported=True, connector="DP-1", width=3840, height=2160, scale=1.5,
                            target_wine_dpi=96, rec_formula="Formula: upscale"),
     "files": config(manage_graphics=True)},
    {"name": "graphics-x11", "args": ["--graphics"], "input": "4\n",
     "repo_files": graphics("GNOME", supported=True, connector="HDMI-1", width=1920, height=1080, scale=1.0),
     "env": {"XDG_SESSION_TYPE": "x11"}},
    {"name": "graphics-unsupported", "args": ["--graphics"], "input": "5\n", "repo_files": graphics("HYPRLAND", supported=False),
     "env": {"XDG_CURRENT_DESKTOP": "Hyprland"}},
    {"name": "graphics-undetected", "args": ["--graphics"], "input": "5\n", "repo_files": graphics()},
]
