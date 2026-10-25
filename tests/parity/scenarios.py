"""Flows the parity harness compares. Each scenario:
    name           short identifier (run.py takes names to run a subset)
    args           arguments to ./torquio
    input          what the user types (all at once; echo is off, so it doesn't appear in the output)
    files          {path relative to $HOME: contents} created before the run ("<HOME>" in the contents is
                   replaced by the scratch $HOME; None leaves a file out)
    compare_files  paths relative to $HOME whose contents must match afterwards
    timeout        seconds (default 120)
    env            environment variables to set (None removes one), including the FAKE_* ones below
    fakes          {program: sh script body} replacing a program for this scenario
    repo_files     {path in the repo: contents} swapped in for this scenario (both copies)
    piped          True: input comes from a pipe, not the terminal (catches input read ahead and lost)
    git_setup      shell commands run in both repo copies first (e.g. an upstream branch with updates);
                   undone afterwards

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
    FAKE_MUTTER_WAYLAND   "yes": `gsettings list-schemas` lists org.gnome.mutter.wayland
    FAKE_PICKED           what the zenity/kdialog file and folder pickers return (unset: cancelled)
    FAKE_CONTAINER_NVIDIA "yes": the container has the NVIDIA libraries
    FAKE_VULKANINFO       `vulkaninfo --summary` output in the container (printf %b)
    FAKE_IMAGE_PRESENT    "yes": the prebuilt image is already downloaded
    FAKE_IMAGES           `podman images` output (printf %b)
    FAKE_PULL_RC, FAKE_COMMIT_RC, FAKE_CREATE_RC, FAKE_NEW_WINE_RC, FAKE_BUILD_RC
                          exit codes of image download, snapshot, container creation, the new container's
                          Wine check and the engine build (default 0)
    FAKE_XEV              "yes": xev is installed in the container
A container machine ID written by the scenario (fix identity, re-created container) is kept in
~/.fake-machine-id and read back from there.

State-changing calls to the fakes are recorded in ~/.fake-calls and compared.
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
CONTAINER = {"FAKE_CONTAINER": "torquio-env", "FAKE_IMAGE": "current", "FAKE_MACHINE_ID": "derived"}
KDE_2X = graphics("KDE", supported=True, connector="DP-2", width=3840, height=2160, scale=2.0, target_wine_dpi=192,
                  target_xwayland_factor=1, rec_formula="Formula: 96 x 2")
COSMIC_15 = graphics("COSMIC", supported=True, connector="HDMI-A-1", width=1920, height=1080, scale=1.5,
                     target_wine_dpi=144, target_xwayland_factor=1, rec_formula="Formula: 96 x 1.5")
COSMIC_FILE = ".config/cosmic/com.system76.CosmicComp/v1/descale_xwayland"
MAPPABLE = {"Music/.keep": "", f"{PREFIX}/dosdevices/.keep": ""}
DORICO_APPDATA = f"{PREFIX}/drive_c/users/me/AppData/Roaming/Steinberg/Dorico 6"
KEYCOMMANDS = {f"{DORICO_APPDATA}/keycommands_en.json": '{"a": 1}', f"{DORICO_APPDATA}/keycommands_de.json": '{"b": 2}',
               f"{DORICO_APPDATA}/Old/keycommands_old.json": "{}"}
VKD3D_CURRENT = {f".local/share/torquio/vkd3d-proton/3.0.1/{dll}": "" for dll in ("d3d12.dll", "d3d12core.dll")}
INSTALLED_FULL = {**INSTALLED, **VKD3D_CURRENT, f"{PREFIX}/system.reg": "WINE REGISTRY Version 2\n"}
VULKANINFO_TWO = ("GPU0:\\n\\tdeviceType         = PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU\\n\\tdeviceName         = Intel(R) Graphics\\n"
                  "GPU1:\\n\\tdeviceType         = PHYSICAL_DEVICE_TYPE_DISCRETE_GPU\\n\\tdeviceName         = NVIDIA RTX 4060\\n"
                  "GPU2:\\n\\tdeviceType         = PHYSICAL_DEVICE_TYPE_CPU\\n\\tdeviceName         = llvmpipe\\n")
OLD_PREBUILT = "ghcr.io/snakeeyes021/torquio-env:build-000000000000"
CANTAI_ACTIVE = {f"{PREFIX}/drive_c/users/me/AppData/Roaming/Cantai/Cantai.settings": '<VALUE name="activationToken" val="tok"/>'}
GIT = "git -c user.name=parity -c user.email=parity@localhost"
UPSTREAM_AHEAD = (f"git checkout -q -b parity-upstream; {GIT} commit -q --allow-empty -m 'Faster key commands'; "
                  f"{GIT} commit -q --allow-empty -m 'Fix for KDE scaling'; git checkout -q -B parity-local HEAD~2; "
                  "git branch -q -u parity-upstream")
UPSTREAM_SAME = "git checkout -q -b parity-upstream; git checkout -q -b parity-local; git branch -q -u parity-upstream"
ACTIVATION_DAT = f"{PREFIX}/drive_c/users/me/AppData/Roaming/Steinberg/Activation Manager/Data/activation.dat"
STEINBERG_ACTIVE = {ACTIVATION_DAT: json.dumps({"ProductPackages": [
    {"ProductPackage": "Dorico Pro 6", "LicensedItems": [{"jwt": "x"}]},
    {"ProductPackage": "HALion Sonic", "LicensedItems": [{"jwt": "y"}]}]})}
STEINBERG_INACTIVE = {ACTIVATION_DAT: json.dumps({"ProductPackages": []})}
AM_WITHOUT_DATA = {f"{PREFIX}/drive_c/Program Files/Steinberg/Activation Manager/x.exe": ""}
PROJECTS = {f"{PREFIX}/drive_c/users/me/Documents/Mine/Song {i}.dorico": "" for i in range(12)}
PROJECTS_SKIPPED = {
    f"{PREFIX}/drive_c/users/me/AppData/Roaming/Steinberg/Dorico 6/AutoSave/a.dorico": "",
    f"{PREFIX}/drive_c/Program Files/Steinberg/Dorico 6/Tutorials/t.dorico": "",
    f"{PREFIX}/drive_c/users/Public/Documents/Dorico Example Projects/e.dorico": "",
    f"{PREFIX}/drive_c/users/me/Temp/Upper.DORICO": "",
}
CONFIRM_ALL = "y\ny\nyes, permanently delete everything\n"
LEFTOVERS = {
    ".local/bin/torquio-dorico": "", ".local/bin/torquio-sam": "", ".local/bin/torquio_graphics.py": "",
    ".local/bin/unrelated-tool": "",
    ".local/share/applications/Dorico.desktop": "", ".local/share/applications/Steinberg Activation Manager.desktop": "",
    ".local/share/applications/wine-protocol-net-steinberg-sam.desktop": "",
    ".local/share/applications/wine-extension-dorico.desktop": "",
    ".local/share/applications/wine-extension-txt.desktop": "Exec=env WINEPREFIX=<HOME>/.local/share/torquio/prefix wine start\n",
    ".local/share/applications/wine-extension-other.desktop": "Exec=env WINEPREFIX=/elsewhere wine start\n",
    ".local/share/mime/packages/x-wine-extension-txt.xml": "", ".local/share/mime/packages/x-wine-extension-other.xml": "",
    ".local/share/mime/packages/application-x-dorico.xml": "", ".local/share/mime/dorico/x.xml": "",
    ".local/share/applications/wine/Programs/Steinberg/Dorico 6.desktop": "Path=<HOME>/.local/share/torquio/prefix/drive_c\n",
    ".local/share/applications/wine/Programs/Other/Notepad.desktop": "Path=/opt/other\n",
    ".config/menus/applications-merged/wine-Programs-Steinberg-Dorico 6.menu": "<Menu><Filename>wine-Programs-Steinberg-Dorico 6.desktop</Filename><Directory>wine-Programs-Steinberg.directory</Directory></Menu>",
    ".config/menus/applications-merged/wine-Programs-Other-Notepad.menu": "<Menu><Filename>wine-Programs-Other-Notepad.desktop</Filename><Directory>wine-Programs-Other.directory</Directory></Menu>",
    ".config/menus/applications-merged/wine-empty.menu": "<Menu></Menu>",
    ".local/share/desktop-directories/wine-Programs-Steinberg.directory": "",
    ".local/share/desktop-directories/wine-Programs-Other.directory": "",
    ".local/share/icons/hicolor/256x256/apps/torquio-dorico.png": "", ".local/share/icons/hicolor/256x256/apps/other.png": "",
    ".config/mimeapps.list": "[Default Applications]\napplication/x-dorico=Dorico.desktop;\ntext/plain=gedit.desktop\nx-scheme-handler/net-steinberg-sam=Steinberg Activation Manager.desktop\n",
    "Desktop/Dorico 6.lnk": "", "Desktop/HALion Sonic.lnk": "", "Desktop/Notes.lnk": "",
    "Desktop/wine-Dorico.desktop": "Exec=env WINEPREFIX=<HOME>/.local/share/torquio/data wine x\n",
    "Desktop/Firefox.desktop": "Exec=firefox\n",
}
GNOME_RESTORE = config(manage_graphics=True, original_scale_factor=0, original_kde_policy="false", original_cosmic_policy="none")
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

    # Configure Graphics & Scaling: every option (stage 2)
    {"name": "graphics-enable-automated-gnome", "args": ["--graphics"], "input": "1\ny\n4\n",
     "repo_files": GNOME_125, "files": dict(INSTALLED), "compare_files": [CONFIG],
     "env": {**CONTAINER, "FAKE_XWAYLAND_FACTOR": "uint32 0", "FAKE_MUTTER_WAYLAND": "yes"}},
    {"name": "graphics-disable-automated-restore-gnome", "args": ["--graphics"], "input": "1\ny\n\n\n5\n",
     "repo_files": GNOME_125, "compare_files": [CONFIG],
     "files": {**INSTALLED, **config(manage_graphics=True, original_scale_factor=0)},
     "env": {**CONTAINER, "FAKE_XWAYLAND_FACTOR": "uint32 1"}},
    {"name": "graphics-disable-automated-keep-gnome", "args": ["--graphics"], "input": "1\ny\nn\n\n5\n",
     "repo_files": GNOME_125, "compare_files": [CONFIG],
     "files": {**INSTALLED, **config(manage_graphics=True, original_scale_factor=2)},
     "env": {**CONTAINER, "FAKE_XWAYLAND_FACTOR": "uint32 1"}},
    {"name": "graphics-automated-kde", "args": ["--graphics"], "input": "1\ny\n1\ny\n\n\n5\n",
     "repo_files": KDE_2X, "files": dict(INSTALLED), "compare_files": [CONFIG],
     "env": {**CONTAINER, "XDG_CURRENT_DESKTOP": "KDE", "FAKE_KDE_POLICY": "false"}},
    {"name": "graphics-automated-cosmic", "args": ["--graphics"], "input": "1\ny\n1\ny\n\n\n5\n",
     "repo_files": COSMIC_15, "files": dict(INSTALLED), "compare_files": [CONFIG, COSMIC_FILE],
     "env": {**CONTAINER, "XDG_CURRENT_DESKTOP": "COSMIC"}},
    {"name": "graphics-automated-cancel", "args": ["--graphics"], "input": "1\nn\n\n5\n", "repo_files": GNOME_125,
     "compare_files": [CONFIG]},
    {"name": "graphics-manual-cancel", "args": ["--graphics"], "input": "1\nN\n\n4\n", "repo_files": GNOME_125,
     "files": config(manage_graphics=True), "compare_files": [CONFIG]},
    {"name": "graphics-set-dpi", "args": ["--graphics"], "input": "2\nabc\n\n2\n120\n\n2\n144\nn\n\n2\n144\ny\n\n5\n",
     "repo_files": GNOME_125, "files": {**INSTALLED, **config(freetype_interpreter=35)}, "env": CONTAINER},
    {"name": "graphics-freetype", "args": ["--graphics"], "input": "3\n2\n\n3\n1\n\n3\n3\n5\n",
     "repo_files": GNOME_125, "files": dict(INSTALLED), "compare_files": [CONFIG], "env": CONTAINER},
    {"name": "graphics-match-physical", "args": ["--graphics"], "input": "4\ny\n\n4\nn\n\n4\ny\n\n5\n",
     "repo_files": GNOME_125, "files": dict(INSTALLED), "compare_files": [CONFIG], "env": CONTAINER},
    {"name": "graphics-match-physical-automated", "args": ["--graphics"], "input": "3\ny\n\n4\n",
     "repo_files": GNOME_125, "files": {**INSTALLED, **config(manage_graphics=True)}, "compare_files": [CONFIG],
     "env": {**CONTAINER, "FAKE_XWAYLAND_FACTOR": "uint32 1"}},
    {"name": "graphics-x11-option-1", "args": ["--graphics"], "input": "1\n\n0\nn\n\n4\n",
     "repo_files": graphics("GNOME", supported=True, width=1920, height=1080, scale=1.0),
     "env": {"XDG_SESSION_TYPE": "x11"}, "compare_files": [CONFIG]},
    {"name": "graphics-unsupported-option-1", "args": ["--graphics"], "input": "1\n\n5\n",
     "repo_files": graphics("HYPRLAND", supported=False), "env": {"XDG_CURRENT_DESKTOP": "Hyprland"}},
    {"name": "graphics-eof-at-confirm", "args": ["--graphics"], "input": "1\n\x04", "repo_files": GNOME_125},

    # Folder mappings (stage 2)
    {"name": "map-folder-flag-drive", "args": ["--map_folder", "Music", "drive"], "files": MAPPABLE},
    {"name": "map-folder-flag-desktop", "args": ["--map_folder", "Music", "desktop"],
     "files": {**MAPPABLE, ".config/user-dirs.dirs": 'XDG_DESKTOP_DIR="$HOME/Bureau"\nXDG_MUSIC_DIR="$HOME/Music"\n'}},
    {"name": "map-folder-flag-desktop-name-taken", "args": ["--map_folder", "Music", "desktop"],
     "input": "My Music\n", "files": {**MAPPABLE, "Desktop/Music": "a file in the way"}},
    {"name": "map-folder-flag-missing", "args": ["--map_folder", "Nowhere", "drive"], "files": MAPPABLE},
    {"name": "map-folder-flag-no-prefix", "args": ["--map_folder", "Music"], "files": {"Music/.keep": ""}},
    {"name": "map-folder-flag-ask-type", "args": ["--map_folder", "Music"], "input": "3\n", "files": MAPPABLE},
    {"name": "map-folder-flag-eof", "args": ["--map_folder", "Music"], "input": "\x04", "files": MAPPABLE},
    {"name": "folder-mappings-menu", "input": "6\n1\n1\n\n1\n1\ny\n\n1\n2\n\n1\n2\n\n2\n1\n\n2\n9\n3\n12\n",
     "files": {**MAPPABLE, **INSTALLED, "Desktop/zeta/.keep": "", "Desktop/Alpha/.keep": ""},
     "env": {**CONTAINER, "FAKE_PICKED": "Music"}},
    {"name": "folder-mappings-menu-nothing", "input": "6\n2\n1\n3\n12\n", "files": {**MAPPABLE, **INSTALLED},
     "env": CONTAINER},
    {"name": "folder-mappings-menu-picker-cancelled", "input": "6\n1\n3\n12\n", "files": {**MAPPABLE, **INSTALLED},
     "env": CONTAINER},

    # Key commands (stage 2)
    {"name": "keycommands-export", "args": ["--export_key_commands"], "files": KEYCOMMANDS},
    {"name": "keycommands-export-no-dorico", "args": ["--export_key_commands"], "files": dict(INSTALLED)},
    {"name": "keycommands-export-no-files", "args": ["--export_key_commands"],
     "files": {f"{DORICO_APPDATA}/preferences.xml": "<x/>"}},
    {"name": "keycommands-import-one", "args": ["--import_key_commands"],
     "files": {"Downloads/keycommands_en.json": "{}"}},
    {"name": "keycommands-import-several", "args": ["--import_key_commands"], "input": "2\n",
     "files": {"Downloads/keycommands_en.json": "{}", "Downloads/keycommands_de.json": "{}"}},
    {"name": "keycommands-import-browse", "args": ["--import_key_commands"], "input": "3\n",
     "files": {"Downloads/keycommands_en.json": "{}", "Downloads/keycommands_de.json": "{}", "other.json": "{}"},
     "env": {"FAKE_PICKED": "other.json"}},
    {"name": "keycommands-import-none", "args": ["--import_key_commands"]},
    {"name": "keycommands-menu", "input": "7\n1\n\n2\n\n3\n12\n",
     "files": {**KEYCOMMANDS, **INSTALLED}, "env": CONTAINER},

    # Other tools (stage 2)
    {"name": "run-exe", "args": ["--run", "setup.exe"], "files": {"setup.exe": "MZ"}, "env": CONTAINER},
    {"name": "run-msi", "args": ["--run", "setup.msi"], "files": {"setup.msi": "x"}, "env": CONTAINER},
    {"name": "run-missing", "args": ["--run", "missing.exe"], "env": CONTAINER},
    {"name": "run-picker", "args": ["--run"], "files": {"Downloads/Tool Setup.exe": "MZ"},
     "env": {**CONTAINER, "FAKE_PICKED": "Downloads/Tool Setup.exe"}},
    {"name": "enable-ntsync", "args": ["--enable-ntsync"], "env": {"FAKE_NTSYNC_MODULE": "yes"}},

    # The same flows with input from a pipe: Python code must leave the rest of the input to the Bash menus
    {"name": "piped-keycommands-menu", "input": "7\n3\n12\n", "piped": True, "files": dict(INSTALLED), "env": CONTAINER},
    {"name": "piped-settings-menu", "input": "11\n1\n2\n12\n", "piped": True, "files": dict(INSTALLED),
     "env": CONTAINER, "compare_files": [CONFIG]},
    {"name": "piped-folder-mappings-menu", "input": "6\n1\n2\n\n3\n12\n", "piped": True,
     "files": {**MAPPABLE, **INSTALLED}, "env": {**CONTAINER, "FAKE_PICKED": "Music"}},
    {"name": "piped-graphics-menu", "input": "4\n3\n3\n5\n12\n", "piped": True, "repo_files": GNOME_125,
     "files": dict(INSTALLED), "env": CONTAINER},
    {"name": "piped-menu-settings-not-installed", "input": "6\n1\n2\n7\n", "piped": True, "compare_files": [CONFIG]},

    # Update Torquio and what runs after it (stage 3)
    {"name": "update-no-upstream", "args": ["--update"]},
    {"name": "update-up-to-date", "args": ["--update"], "git_setup": UPSTREAM_SAME},
    {"name": "update-local-changes", "args": ["--update"],
     "git_setup": UPSTREAM_AHEAD + "; echo changed >> README.md"},
    {"name": "update-cancel", "args": ["--update"], "input": "n\n", "git_setup": UPSTREAM_AHEAD},
    {"name": "update-install-not-installed", "args": ["--update"], "input": "\n", "git_setup": UPSTREAM_AHEAD},
    {"name": "update-eof", "args": ["--update"], "input": "\x04", "git_setup": UPSTREAM_AHEAD},
    {"name": "update-from-menu", "input": "4\n\n\n7\n", "git_setup": UPSTREAM_AHEAD},
    {"name": "update-from-menu-eof", "input": "4\n\x04", "git_setup": UPSTREAM_AHEAD, "timeout": 30},
    {"name": "update-install-installed", "args": ["--update"], "input": "y\n", "git_setup": UPSTREAM_AHEAD,
     "files": INSTALLED_FULL, "env": {**CONTAINER, "FAKE_CONTAINER_NVIDIA": "yes"}},
    {"name": "post-update-current", "args": ["--post-update", "HEAD"], "files": INSTALLED_FULL,
     "env": {**CONTAINER, "FAKE_CONTAINER_NVIDIA": "yes"}},
    {"name": "post-update-menu", "args": ["--post-update", "HEAD", "--menu"], "input": "\n12\n",
     "files": INSTALLED_FULL, "env": {**CONTAINER, "FAKE_CONTAINER_NVIDIA": "yes"}},
    {"name": "post-update-engine-changed", "args": ["--post-update", "HEAD~3"], "input": "n\n",
     "files": INSTALLED_FULL, "env": {**CONTAINER, "FAKE_IMAGE": OLD_PREBUILT, "FAKE_CONTAINER_NVIDIA": "yes"}},
    {"name": "post-update-download-engine", "args": ["--post-update", "HEAD"], "input": "\n",
     "files": INSTALLED_FULL,
     "env": {**CONTAINER, "FAKE_IMAGE": OLD_PREBUILT, "FAKE_CONTAINER_NVIDIA": "yes",
             "FAKE_IMAGES": f"{OLD_PREBUILT}\\nghcr.io/snakeeyes021/torquio-env:build-111111111111\\ndocker.io/library/ubuntu:24.04\\n"}},
    {"name": "post-update-new-container-broken", "args": ["--post-update", "HEAD"], "input": "\n",
     "files": INSTALLED_FULL,
     "env": {**CONTAINER, "FAKE_IMAGE": OLD_PREBUILT, "FAKE_CONTAINER_NVIDIA": "yes", "FAKE_NEW_WINE_RC": "1"}},
    {"name": "post-update-image-unavailable", "args": ["--post-update", "HEAD"], "input": "\nn\n",
     "files": INSTALLED_FULL,
     "env": {**CONTAINER, "FAKE_IMAGE": OLD_PREBUILT, "FAKE_CONTAINER_NVIDIA": "yes", "FAKE_PULL_RC": "1"}},
    {"name": "post-update-compiled-engine", "args": ["--post-update", "HEAD"], "input": "y\n",
     "files": INSTALLED_FULL,
     "env": {**CONTAINER, "FAKE_IMAGE": "localhost/torquio-env:latest", "FAKE_BUILD_INFO": "",
             "FAKE_CONTAINER_NVIDIA": "yes"}},
    {"name": "post-update-identity", "args": ["--post-update", "HEAD"], "input": "y\n", "files": INSTALLED_FULL,
     "env": {**CONTAINER, "FAKE_MACHINE_ID": "0123456789abcdef0123456789abcdef", "FAKE_CONTAINER_NVIDIA": "yes"}},
    {"name": "post-update-nvidia", "args": ["--post-update", "HEAD"], "input": "\n", "files": INSTALLED_FULL,
     "env": CONTAINER},
    {"name": "post-update-not-installed", "args": ["--post-update", "HEAD"]},

    # Engine, container, identity, GPU (stage 3)
    {"name": "rebuild-wine", "args": ["--rebuild-wine"], "files": INSTALLED_FULL, "env": CONTAINER},
    {"name": "rebuild-wine-fails", "args": ["--rebuild-wine"], "files": INSTALLED_FULL,
     "env": {**CONTAINER, "FAKE_BUILD_RC": "3"}},
    {"name": "rebuild-wine-no-container", "args": ["--rebuild-wine"]},
    {"name": "setup-gpu-nvidia-snapshot", "args": ["--setup-gpu"], "input": "\n", "files": INSTALLED_FULL,
     "env": {**CONTAINER, "FAKE_IMAGE": "localhost/torquio-env:gpu-20260101000000",
             "FAKE_IMAGES": "localhost/torquio-env:gpu-20260101000000\\n"}},
    {"name": "setup-gpu-snapshot-fails", "args": ["--setup-gpu"], "input": "y\n", "files": INSTALLED_FULL,
     "env": {**CONTAINER, "FAKE_IMAGE": "localhost/torquio-env:latest", "FAKE_COMMIT_RC": "1"}},
    {"name": "setup-gpu-declined", "args": ["--setup-gpu"], "input": "n\n", "files": INSTALLED_FULL, "env": CONTAINER},
    {"name": "setup-gpu-ready", "args": ["--setup-gpu"], "files": INSTALLED_FULL,
     "env": {**CONTAINER, "FAKE_CONTAINER_NVIDIA": "yes"}},
    {"name": "fix-identity-stable", "args": ["--fix-identity"], "env": CONTAINER},
    {"name": "fix-identity-no-container", "args": ["--fix-identity"]},
    {"name": "fix-identity-cantai-active", "args": ["--fix-identity"], "files": CANTAI_ACTIVE,
     "env": {**CONTAINER, "FAKE_MACHINE_ID": "0123456789abcdef0123456789abcdef"}},
    {"name": "fix-identity-change", "args": ["--fix-identity"], "input": "y\n",
     "env": {**CONTAINER, "FAKE_MACHINE_ID": "0123456789abcdef0123456789abcdef"}},
    {"name": "fix-identity-decline", "args": ["--fix-identity"], "input": "\n",
     "env": {**CONTAINER, "FAKE_MACHINE_ID": "0123456789abcdef0123456789abcdef"}},
    {"name": "wine-tools-programs", "input": "8\n1\n\n2\n\n3\n\n4\n\n5\n\n6\n\n7\n\n10\n11\n\n14\n12\n",
     "files": INSTALLED_FULL, "env": CONTAINER},
    {"name": "wine-tools-xev", "input": "8\n8\nn\n8\n\n\n14\n12\n", "files": INSTALLED_FULL, "env": CONTAINER},
    {"name": "wine-tools-engine", "input": "8\n12\nn\n\n12\ny\n\n14\n12\n", "files": INSTALLED_FULL,
     "env": {**CONTAINER, "FAKE_CONTAINER_NVIDIA": "yes"}},
    {"name": "wine-tools-gpu-chooser", "input": "8\n13\n2\n2\n2\n9\n3\n1\n4\n14\n12\n",
     "files": INSTALLED_FULL, "compare_files": [CONFIG],
     "env": {**CONTAINER, "FAKE_CONTAINER_NVIDIA": "yes", "FAKE_VULKANINFO": VULKANINFO_TWO}},
    {"name": "wine-tools-gpu-chooser-none", "input": "8\n13\n2\n\n4\n14\n12\n", "files": INSTALLED_FULL,
     "compare_files": [CONFIG], "env": {**CONTAINER, "FAKE_CONTAINER_NVIDIA": "yes"}},
    {"name": "refresh-launchers-menu", "input": "5\n\n12\n", "files": INSTALLED_FULL, "env": CONTAINER},

    # Uninstall (stage 4)
    {"name": "uninstall-steinberg-active-cancel", "args": ["--uninstall"], "input": "no\n",
     "files": {**INSTALLED, **STEINBERG_ACTIVE}},
    {"name": "uninstall-steinberg-and-cantai-active-override", "args": ["--uninstall"],
     "input": "yes, I'm aware my license is active and deleting it will prevent me from ever deactivating it. proceed anyways\nn\n",
     "files": {**INSTALLED, **STEINBERG_ACTIVE, **CANTAI_ACTIVE}},
    {"name": "uninstall-cantai-active-unknown-steinberg", "args": ["--uninstall"], "input": "\n",
     "files": {**INSTALLED, **AM_WITHOUT_DATA, **CANTAI_ACTIVE}},
    {"name": "uninstall-unknown-override", "args": ["--uninstall"],
     "input": "no, I promise, I've deactivated my license\nn\n", "files": {**INSTALLED, **AM_WITHOUT_DATA}},
    {"name": "uninstall-unreadable-activation", "args": ["--uninstall"], "input": "x\n",
     "files": {**INSTALLED, ACTIVATION_DAT: "{broken"}},
    {"name": "uninstall-projects-cancel", "args": ["--uninstall"], "input": "y\nno\n",
     "files": {**INSTALLED, **STEINBERG_INACTIVE, **PROJECTS, **PROJECTS_SKIPPED}},
    {"name": "uninstall-final-confirmation-wrong", "args": ["--uninstall"], "input": "y\ny\nyes\n",
     "files": {**INSTALLED, **STEINBERG_INACTIVE}},
    {"name": "uninstall-eof", "args": ["--uninstall"], "input": "y\n\x04", "files": dict(INSTALLED)},
    {"name": "uninstall-everything", "args": ["--uninstall"], "input": CONFIRM_ALL,
     "files": {**INSTALLED_FULL, **LEFTOVERS, **config(ai_gpu="auto")}, "compare_files": [".config/mimeapps.list"],
     "env": {**CONTAINER, "FAKE_IMAGES": f"{OLD_PREBUILT}\\nlocalhost/torquio-env:gpu-20260101000000\\nlocalhost/other:1\\n"}},
    {"name": "uninstall-with-projects-and-restore", "args": ["--uninstall"],
     "input": "y\nyes, I've saved my projects elsewhere or I'm ok with losing them\nyes, permanently delete everything\n\nn\n\n",
     "files": {**INSTALLED, **PROJECTS, **GNOME_RESTORE, COSMIC_FILE: "fractional\n"},
     "env": {**CONTAINER, "FAKE_XWAYLAND_FACTOR": "uint32 1", "FAKE_KDE_POLICY": "true"}},
    {"name": "uninstall-from-menu-cancel", "input": "2\nn\n\n12\n", "files": dict(INSTALLED), "env": CONTAINER},
    {"name": "uninstall-from-menu", "input": f"2\n{CONFIRM_ALL}7\n", "files": dict(INSTALLED_FULL), "env": CONTAINER},
]
