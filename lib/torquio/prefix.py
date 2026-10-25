"""Commands for the Wine prefix, run inside the container.

The scripts are the same text the Bash version sends to `distrobox enter ... -- bash -c`, so the container
sees exactly what it did before.
"""
import os

from . import paths, run


def env_script(freetype=None):
    """The `export ...;` preamble every prefix command starts with."""
    script = f'export WINEPREFIX="{paths.prefix_dir()}"; export PATH="{paths.WINE_CUSTOM_BIN}:$PATH"; '
    if freetype is not None:
        script += f'export FREETYPE_PROPERTIES="truetype:interpreter-version={freetype}"; '
    return script


def enter_quietly(script):
    """distrobox enter ... -- bash -c SCRIPT >/dev/null 2>&1 || true (input from the terminal, as in Bash)."""
    run.interactive(["distrobox", "enter", paths.container_name(), "--", "bash", "-c", script],
                    stdout=run.DEVNULL, stderr=run.DEVNULL)


def enter_visibly(script):
    """distrobox enter ... -- bash -c SCRIPT || true, output and input on the terminal."""
    run.interactive(["distrobox", "enter", paths.container_name(), "--", "bash", "-c", script])


def set_dpi(dpi, freetype):
    enter_quietly(env_script(freetype) + f'wine reg add "HKCU\\Control Panel\\Desktop" /v LogPixels /t REG_DWORD /d {dpi} /f')


def set_focus_options():
    enter_quietly(env_script() + 'wine reg add "HKCU\\Software\\Wine\\X11 Driver" /v FocusOnClick /t REG_SZ /d Y /f && '
                  'wine reg add "HKCU\\Software\\Wine\\X11 Driver" /v UseTakeFocus /t REG_SZ /d N /f')


def restart_wineserver():
    """Stop every Wine program in the prefix (changes to the registry take effect on the next start)."""
    enter_quietly(env_script() + "wineserver -k && wineserver -w")


def apply_settings():
    """apply_prefix_settings: prefix settings every engine needs (re-applied after engine updates)."""
    if not os.path.isfile(os.path.join(paths.prefix_dir(), "system.reg")):
        return
    script = (env_script() + "export WINEDEBUG=-all\n"
              "        wine reg add 'HKCU\\Software\\Wine\\Fonts\\Replacements' /v 'Segoe UI' /t REG_SZ /d Tahoma /f\n"
              "        wine reg add 'HKCU\\Software\\Wine\\AppDefaults\\rundll32.exe\\DllOverrides' /v '*mscoree' /t REG_SZ /d '' /f\n"
              "        wineserver -w")
    run.interactive(["distrobox", "enter", paths.container_name(), "--", "bash", "-c", script],
                    stdin=run.DEVNULL, stdout=run.DEVNULL, stderr=run.DEVNULL)


def windows_path(unix_path):
    """`winepath -w` for a host path (stderr shows on the terminal, as in Bash)."""
    script = f'export WINEDEBUG=-all; {env_script().rstrip()} winepath -w "{unix_path}"'
    return run.capture(["distrobox", "enter", paths.container_name(), "--", "bash", "-c", script],
                       stderr=None, stdin=None)[1].replace("\r", "").rstrip("\n")

