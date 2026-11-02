"""Running Torquio on the host. Everything Torquio does happens there (distrobox, the container, the Wine prefix,
the launchers in ~/.local/bin), so the GUI drives the host's copy of Torquio: through `flatpak-spawn --host`
inside the Flatpak sandbox, directly otherwise. Torquio answers `torquio api VERB` with JSON (docs/GUI.md)."""
import json
import os
import subprocess

# The oldest `torquio api` this GUI understands
MIN_API = 1
IN_FLATPAK = os.path.exists("/.flatpak-info")


class NotInstalled(Exception):
    """There's no Torquio on the host."""


class TooOld(Exception):
    """The host's Torquio predates the API this GUI needs (it can be updated)."""


class HostError(Exception):
    """A host command failed; the message is for the user."""


def command(cmd):
    """`cmd` as it has to run to reach the host."""
    return ["flatpak-spawn", "--host", *cmd] if IN_FLATPAK else list(cmd)


def run(cmd, timeout=60):
    """Run on the host without input; returns (exit code, stdout)."""
    try:
        p = subprocess.run(command(cmd), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, text=True, timeout=timeout)
    except FileNotFoundError:
        return 127, ""
    except subprocess.TimeoutExpired:
        return 124, ""
    return p.returncode, p.stdout


def spawn(cmd):
    """Start on the host and don't wait (launching Dorico and the like)."""
    subprocess.Popen(command(cmd), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def torquio():
    """The host's `torquio`: the link the installer puts in ~/.local/bin (the same path inside and outside the
    sandbox, which shares $HOME's path)."""
    path = os.path.join(os.path.expanduser("~"), ".local/bin/torquio")
    code, _ = run(["test", "-x", path], timeout=10)
    if code == 0:
        return path
    raise NotInstalled()


def launcher(name):
    """A Torquio launcher in ~/.local/bin (torquio-dorico, torquio-sam, torquio-sda-handler)."""
    return os.path.join(os.path.expanduser("~"), ".local/bin", name)


def api(verb, *args, timeout=120):
    """`torquio api VERB ARGS...` as data."""
    code, out = run([torquio(), "api", verb, *args], timeout=timeout)
    try:
        data = json.loads(out.strip().splitlines()[-1]) if out.strip() else None
    except (ValueError, IndexError):
        data = None
    if not isinstance(data, dict):
        # Torquio before the API treats `api` as an unknown option
        raise TooOld()
    if code != 0:
        raise HostError(data.get("error", f"torquio api {verb} failed (exit code {code})"))
    return data


def check_version():
    """The host's `torquio api version`, if this GUI can use it (raises TooOld otherwise)."""
    data = api("version", timeout=30)
    if data.get("api", 0) < MIN_API:
        raise TooOld()
    return data
