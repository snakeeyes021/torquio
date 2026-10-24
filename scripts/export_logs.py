#!/usr/bin/env python3
"""Collect Torquio, Wine and Steinberg logs plus a system summary into one zip for bug reports.

Personal data is redacted from every file (email addresses, sign-in tokens, the Steinberg hardware ID and
license grant IDs). License data, registry files and crash dumps are never included; crash dumps are only
listed. Project file names still appear in the logs.

Usage: export_logs.py [OUTPUT_DIR]   (default: the XDG download directory)
Prints the path of the zip it wrote.
"""
import datetime
import getpass
import glob
import os
import platform
import re
import socket
import subprocess
import sys
import zipfile

import version_manifest

HOME = os.path.expanduser("~")
DATA_DIR = os.environ.get("TORQUIO_DATA_DIR") or os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.join(HOME, ".local/share"), "torquio")
PREFIX = os.environ.get("TORQUIO_PREFIX_DIR") or os.path.join(DATA_DIR, "prefix")
CONTAINER = os.environ.get("TORQUIO_CONTAINER_NAME") or "torquio-env"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_FILE = 20 << 20  # keep only the last 20 MB of any single log

# (folder in the zip, glob relative to the prefix's drive_c/users/<user>/)
PREFIX_LOGS = [
    ("dorico", "AppData/Roaming/Steinberg/Dorico */application*.log"),
    ("audio-engine", "AppData/Roaming/Steinberg/Dorico * AudioEngine_64/logs/*.log"),
    ("activation-manager", "AppData/Roaming/Steinberg/Activation Manager/Logs/*.txt"),
    ("activation-manager/clients", "AppData/Roaming/Steinberg/Activation Manager/Logs/Clients/*.txt"),
    ("steinberg-runtime", "AppData/Roaming/Steinberg/Steinberg Runtime/Logs/*.txt"),
    ("download-assistant", "AppData/Local/Steinberg Download Assistant/logs/*.log"),
    ("other", "AppData/Local/Temp/Steinberg Library Manager.log"),
    ("other", "AppData/Local/Temp/NotePerformer64.log"),
]

EMAIL = re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
REDACTIONS = [
    (re.compile(rb"eyJ[A-Za-z0-9_-]{8,}(?:\.[A-Za-z0-9_-]+){0,2}"), b"<token>"),
    (re.compile(rb"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"), rb"\1<token>"),
    (re.compile(rb"(?i)((?:access|refresh|id)[ _]token[\"']?\s*[:=]\s*[\"']?)[^\s\"',}&<]{20,}"), rb"\1<token>"),
    # One-time sign-in codes and tokens passed in web addresses (e.g. a login redirect), should one be logged
    (re.compile(rb"(?i)([?&#](?:code|code_verifier|access_token|id_token|refresh_token|token)=)[^&\s\"'<>]+"), rb"\1<token>"),
    (re.compile(rb"(?i)(hardware ID:\s*)[0-9a-f]+"), rb"\1<hardware-id>"),
    (re.compile(rb"(?i)(grant(?:ID)?:?\s*)[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"), rb"\1<grant-id>"),
]


# In the Activation Manager's, audio engine's and Download Assistant's logs every GUID-shaped value is a
# license, grant, lease, session or owned-product ID; elsewhere (e.g. Wine's output) GUIDs identify Windows
# components and stay.
LICENSE_LOGS = ("activation-manager", "audio-engine", "download-assistant")
GUID = re.compile(rb"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")


# Stock computer names that also appear in logs for other reasons (e.g. "OS: Bazzite"); left alone.
COMMON_HOSTNAMES = {"localhost", "linux", "fedora", "bazzite", "nobara", "ubuntu", "debian", "mint", "arch",
                    "archlinux", "manjaro", "endeavouros", "cachyos", "opensuse", "pop-os", "steamdeck"}
PATH_SEP = rb"(?:/|\\+)"


def personal_patterns(texts):
    """Patterns for this user's own identifiers: full email addresses, the first half of any address
    found (when it is a whole folder or file name, e.g. a cloud-sync folder), the username in paths and
    after labels like "UserName:", and the computer name. Email halves are only matched as path parts so that a common word like
    "info" is never blanked from ordinary log text."""
    patterns = [(EMAIL, b"<email>")]
    names = {m.split(b"@")[0] for text in texts for m in EMAIL.findall(text)}
    for name in sorted(names, key=len, reverse=True):
        if len(name) >= 3:
            patterns.append((re.compile(rb"(?i)(?<=[/\\])" + re.escape(name) + rb"(?=[/\\\"']|$)", re.M), b"<email-name>"))
    users = {getpass.getuser(), os.path.basename(HOME)}
    users |= {os.path.basename(d) for d in glob.glob(os.path.join(PREFIX, "drive_c/users/*"))}
    for user in sorted(users - {"Public", "public", ""}, key=len, reverse=True):
        patterns.append((re.compile(rb"(?i)(" + PATH_SEP + rb"(?:home|users)" + PATH_SEP + rb")" + re.escape(user.encode())
                                    + rb"(?![A-Za-z0-9._-])"), rb"\1<user>"))
        patterns.append((re.compile(rb"(?i)((?:user ?name|user)\s*[:=]\s*|started by\s+)" + re.escape(user.encode())
                                    + rb"(?![A-Za-z0-9._-])"), rb"\1<user>"))
    host = socket.gethostname().split(".")[0]
    if len(host) >= 3 and host.lower() not in COMMON_HOSTNAMES:
        patterns.append((re.compile(rb"(?i)(?<![A-Za-z0-9])" + re.escape(host.encode()) + rb"(?![A-Za-z0-9])"), b"<computer>"))
    return patterns


PERSONAL = []  # filled in by main() once all logs are read


def redact(data, folder=""):
    for pattern, replacement in PERSONAL + REDACTIONS:
        data = pattern.sub(replacement, data)
    if folder.startswith(LICENSE_LOGS):
        data = GUID.sub(b"<id>", data)
    return data


def read_log(path):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        if size > MAX_FILE:
            f.seek(size - MAX_FILE)
            return b"[... only the last 20 MB of this log are included ...]\n" + f.read()
        return f.read()


def run(cmd, timeout=20):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (out.stdout or out.stderr).strip()
    except (OSError, subprocess.SubprocessError) as e:
        return f"(unavailable: {type(e).__name__})"


def system_info():
    lines = [f"Exported: {datetime.datetime.now().astimezone():%Y-%m-%d %H:%M:%S %z}", ""]
    git = ["git", "-C", REPO]
    lines += ["== Torquio",
              f"Version: {run(git + ['describe', '--always', '--dirty', '--tags'])} "
              f"(branch {run(git + ['rev-parse', '--abbrev-ref', 'HEAD'])})", ""]
    os_name = "unknown"
    try:
        os_name = re.search(r'^PRETTY_NAME="?(.*?)"?$', open("/etc/os-release").read(), re.M).group(1)
    except (OSError, AttributeError):
        pass
    cpu = re.search(r"^model name\s*:\s*(.*)$", open("/proc/cpuinfo").read(), re.M) if os.path.exists("/proc/cpuinfo") else None
    mem = re.search(r"^MemTotal:\s*(\d+)", open("/proc/meminfo").read(), re.M) if os.path.exists("/proc/meminfo") else None
    gpus = [l for l in run(["lspci"]).splitlines() if re.search(r"VGA|3D|Display", l)]
    lines += ["== System",
              f"OS: {os_name}", f"Kernel: {platform.release()}",
              f"Desktop: {os.environ.get('XDG_CURRENT_DESKTOP', '?')} ({os.environ.get('XDG_SESSION_TYPE', '?')})",
              f"CPU: {cpu.group(1) if cpu else '?'}", f"Memory: {int(mem.group(1)) // 1024} MB" if mem else "Memory: ?"]
    lines += [f"GPU: {g.split(': ', 1)[-1]}" for g in gpus] or ["GPU: ?"]
    lines += [f"ntsync: {'/dev/ntsync present' if os.path.exists('/dev/ntsync') else 'no /dev/ntsync'}", ""]
    containers = run(["distrobox", "list"])
    lines += ["== Container",
              f"Distrobox: {run(['distrobox', '--version'])}",
              f"Podman: {run(['podman', '--version'])}" if run(["sh", "-c", "command -v podman"]) else f"Docker: {run(['docker', '--version'])}",
              f"Container '{CONTAINER}': {'present' if CONTAINER in containers else 'missing'}"]
    if CONTAINER in containers:
        wine = [l for l in run(["distrobox", "enter", CONTAINER, "--", "/opt/wine-custom/bin/wine", "--version"], timeout=90).splitlines() if l.startswith("wine-")]
        lines.append(f"Wine: {wine[-1] if wine else '?'}")
    lines.append("")
    try:
        config = open(os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config"), "torquio/config.json")).read().strip()
    except OSError:
        config = "(none)"
    lines += ["== Torquio settings", config, ""]
    state = run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "steinberg_license_state.py"), PREFIX])
    lines += ["== Steinberg licenses activated in this installation", state.replace("\n", ": ", 1).replace("\n", ", "), ""]
    manifest, warnings = version_manifest.manifest()
    lines += ["== Version manifest (Wine engine and installed Windows software)"] + manifest + [f"Warning: {w}" for w in warnings] + [""]
    dumps = sorted(glob.glob(os.path.join(PREFIX, "drive_c/users/*/Documents/Steinberg/CrashDumps/*.dmp")), key=os.path.getmtime, reverse=True)
    lines.append("== Crash dumps (not included, listed only; newest first)")
    lines += [f"{datetime.datetime.fromtimestamp(os.path.getmtime(d)):%Y-%m-%d %H:%M}  {os.path.getsize(d):>9} bytes  {os.path.basename(d)}"
              for d in dumps[:20]] or ["(none)"]
    return "\n".join(lines).encode() + b"\n"


README = b"""Torquio log export

system-info.txt   Torquio version, system, container, settings, Wine engine and installed Windows software
torquio/          Torquio's own logs (these include Wine's output while Dorico runs)
dorico/, audio-engine/, activation-manager/, steinberg-runtime/, download-assistant/, other/
                  logs written by Dorico and the Steinberg tools inside the Wine prefix

Removed from every file: email addresses (and their first half where it is a folder or file name), your
username in paths, your computer's name, sign-in tokens, the Steinberg hardware ID and license IDs.
Never included: license data, Wine registry files, crash dumps (listed in system-info.txt only).
Still present: names and folder paths of projects opened in Dorico.
"""


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else run(["xdg-user-dir", "DOWNLOAD"]) or os.path.join(HOME, "Downloads")
    if not os.path.isdir(out_dir):
        out_dir = os.path.join(HOME, "Downloads")
    os.makedirs(out_dir, exist_ok=True)
    zip_path = os.path.join(out_dir, f"torquio-logs-{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}.zip")
    logs = []  # (folder in the zip, file name, contents)
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "logs", "*.log")) + glob.glob(os.path.join(DATA_DIR, "*.log"))):
        logs.append(("torquio", os.path.basename(path), read_log(path)))
    for user_dir in sorted(glob.glob(os.path.join(PREFIX, "drive_c/users/*"))):
        for folder, pattern in PREFIX_LOGS:
            for path in sorted(glob.glob(os.path.join(user_dir, pattern))):
                if os.path.isfile(path):
                    # Name Dorico's logs after their version folder ("Dorico 6 - application.log")
                    version_dir = {"dorico": 1, "audio-engine": 2}.get(folder)
                    name = os.path.basename(path)
                    if version_dir:
                        name = f"{os.path.basename(os.path.dirname(path) if version_dir == 1 else os.path.dirname(os.path.dirname(path)))} - {name}"
                    logs.append((folder, name, read_log(path)))
    info = system_info()
    PERSONAL.extend(personal_patterns([data for _, _, data in logs] + [info]))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", README)
        z.writestr("system-info.txt", redact(info))
        for folder, name, data in logs:
            z.writestr(f"{folder}/{name}", redact(data, folder))
    print(zip_path)


if __name__ == "__main__":
    main()
