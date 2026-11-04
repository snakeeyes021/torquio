"""Keeping MediaBay up to date. The Download Assistant downloads MediaBay updates itself but can't install them
under Wine: Setup.exe checks the signature of the update's preinstall.ps1, which Wine can't verify (error 231),
and the Download Assistant tries again, and fails again, every time it starts. Torquio installs the download it
leaves behind the way it installs the user's MediaBay zip (without preinstall.ps1), so the Download Assistant
then finds MediaBay up to date."""
import glob
import os
import re
import shlex
import zipfile

from . import manifest, paths, run, versions

ZIP = "MediaBay_Installer_win64.zip"


def installed_version():
    for name, values in manifest.installed_programs().items():
        if name.startswith("Steinberg MediaBay"):
            return values.get("DisplayVersion", "")
    return ""


def zip_version(path):
    """The version of the MediaBay installer in a zip ("MediaBay 1.4.10/Setup.exe"), or ""."""
    try:
        with zipfile.ZipFile(path) as z:
            found = [m.group(1) for m in (re.match(r"MediaBay ([0-9][0-9.]*)/Setup\.exe$", n) for n in z.namelist())
                     if m]
    except (OSError, zipfile.BadZipFile):
        return ""
    return versions.sort(found)[-1] if found else ""


def tried_marker(version):
    """Left in the prefix once Torquio has installed (or tried to install) a MediaBay update, so a failing
    installer isn't run again every time."""
    return os.path.join(paths.prefix_dir(), f".torquio_mediabay_update_{version}")


def failed_update():
    """(zip, version) of the newest MediaBay the Download Assistant downloaded (it leaves the zip in a folder of
    the prefix's Temp; the status file reporting error 231 doesn't stay: the Download Assistant reads and removes
    it on its next start), when it's newer than the installed MediaBay and not tried before; else None."""
    pattern = os.path.join(glob.escape(paths.prefix_dir()), "drive_c/users/*/AppData/Local/Temp/*", ZIP)
    best = None
    for zip_path in glob.glob(pattern):
        version = zip_version(zip_path)
        if version and (best is None or versions.compare(version, best[1]) > 0):
            best = (zip_path, version)
    if best and versions.compare(best[1], installed_version() or "0") > 0 and not os.path.exists(tried_marker(best[1])):
        return best
    return None


def install_failed_update():
    """Install the MediaBay update the Download Assistant couldn't. Returns 0 (also when there's none) or the
    installer's exit code. Only call it with Dorico and Steinberg's programs closed."""
    found = failed_update()
    if not found:
        return 0
    zip_path, version = found
    print(f"Installing the MediaBay update the Download Assistant couldn't install ({version})...")
    script = ('pkill -f "[S]teinbergMediaBayServer.exe" 2>/dev/null; '
              f'cd "{paths.repo_dir()}" && ./scripts/2-install/install_mediabay.sh --zip {shlex.quote(zip_path)}')
    code = run.interactive(["distrobox", "enter", paths.container_name(), "--", "bash", "-c", script])
    try:
        open(tried_marker(version), "w").close()
    except OSError:
        pass
    return code
