"""What installed plug-ins need beyond their own installers. Cantai's editor is a web view and needs the WebView2
runtime; its renderer runs part of its model on the GPU through vkd3d-proton. Torquio's Cantai installer
(scripts/2-install/install_cantai.sh) sets both up; a Cantai installed any other way (Run Custom Installer, the
app's "run a Windows program") gets them from here, which runs after those, on Update and Fix Icons & Refresh
Launchers, and when Dorico starts."""
import glob
import os
import re

from . import paths, run


def _prefix(*parts):
    return os.path.join(glob.escape(paths.prefix_dir()), *parts)


def cantai_installed():
    return bool(glob.glob(_prefix("drive_c/users/*/AppData/Local/Programs/Common/VST3/Cantai.vst3")) or
                glob.glob(_prefix("drive_c/Program Files/Common Files/VST3/Cantai.vst3")))


def webview2_ready():
    """The runtime is in the prefix and the prefix points at it (HKCU\\Environment, see install_webview2.sh)."""
    if not glob.glob(_prefix("drive_c/Program Files/Torquio/WebView2/*/msedgewebview2.exe")):
        return False
    try:
        with open(os.path.join(paths.prefix_dir(), "user.reg"), encoding="utf-8", errors="replace") as f:
            return "WEBVIEW2_BROWSER_EXECUTABLE_FOLDER" in f.read()
    except OSError:
        return False


def vkd3d_ready():
    """The version install_vkd3d_proton.sh pins is in place."""
    try:
        with open(os.path.join(paths.repo_dir(), SCRIPTS["vkd3d-proton"]), encoding="utf-8") as f:
            version = re.search(r'^VKD3D_PROTON_VERSION="([^"]+)"', f.read(), re.M).group(1)
    except (OSError, AttributeError):
        return True  # nothing to compare with; don't download on every start
    folder = os.path.join(paths.data_dir(), "vkd3d-proton", version)
    return all(os.path.isfile(os.path.join(folder, dll)) for dll in ("d3d12.dll", "d3d12core.dll"))


def missing():
    """What installed plug-ins still need: a list of "webview2" / "vkd3d-proton"."""
    if not cantai_installed():
        return []
    return [name for name, ready in (("webview2", webview2_ready), ("vkd3d-proton", vkd3d_ready)) if not ready()]


SCRIPTS = {"webview2": "scripts/2-install/install_webview2.sh",
           "vkd3d-proton": "scripts/2-install/install_vkd3d_proton.sh"}
WHAT = {"webview2": "Cantai's editor needs the WebView2 runtime; setting it up (a one-time download of about 200 MB)...",
        "vkd3d-proton": "Cantai renders faster on the GPU with vkd3d-proton; setting it up..."}


def provision():
    """Set up what installed plug-ins need (nothing when it's all there). Returns 0, or 1 if something failed
    (each part is independent; what failed is said, and the next run tries again)."""
    failed = 0
    for name in missing():
        print(WHAT[name])
        if run.interactive([os.path.join(paths.repo_dir(), SCRIPTS[name])]) != 0:
            print(f"Couldn't set up {name}; Torquio tries again next time.")
            failed = 1
    return failed
