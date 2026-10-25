"""The per-session log every Torquio command and launcher writes to ~/.local/share/torquio/logs.

Same as the Bash version's `exec > >(tee -i LOG) 2>&1`: stdout and stderr (of Torquio and everything it
runs) go through a `tee -i` child into the log, so programs see the same pipe they always did. The 20 newest
logs are kept.
"""
import glob
import os
import subprocess
import sys
import time

from . import paths

KEEP = 20


def prune():
    logs = glob.glob(os.path.join(glob.escape(paths.log_dir()), "*.log"))
    logs.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0, reverse=True)
    for old in logs[KEEP:]:
        try:
            os.remove(old)
        except OSError:
            pass


def start(kind, label, script):
    """Start mirroring this process's output into torquio_KIND_<time>.log and print the log's header
    ("=== Torquio LABEL Log Started: <date> ===", "Script: SCRIPT")."""
    os.makedirs(paths.log_dir(), exist_ok=True)
    log_file = os.path.join(paths.log_dir(), f"torquio_{kind}_{time.strftime('%Y-%m-%d_%H-%M-%S')}.log")
    sys.stdout.flush()
    sys.stderr.flush()
    tee = subprocess.Popen(["tee", "-i", log_file], stdin=subprocess.PIPE)
    os.dup2(tee.stdin.fileno(), 1)
    os.dup2(tee.stdin.fileno(), 2)
    tee.stdin.close()
    sys.stdout.reconfigure(line_buffering=True)  # keep the order right next to the output of child programs
    prune()
    date = subprocess.run(["date"], stdout=subprocess.PIPE, text=True).stdout.rstrip("\n")
    print(f"=== Torquio {label} Log Started: {date} ===")
    print(f"Script: {script}")
    print("=========================================", flush=True)
    return log_file
