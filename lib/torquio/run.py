"""Running other programs. Always with argument lists, never shell strings.

Pick deliberately per call:
- interactive(): the program uses the terminal as if Torquio weren't there (winetricks, sudo, podman's
  progress bars, distrobox's first-start setup).
- capture(): Torquio wants the output. The program gets no input, so it can't swallow keystrokes meant for
  a later prompt (a background `distrobox enter` used to).
- succeeds(): only whether it worked matters.
"""
import shutil
import subprocess
import sys

DEVNULL = subprocess.DEVNULL


def interactive(cmd, **kwargs):
    """Run with the terminal inherited; returns the exit code (127 if the program doesn't exist)."""
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        return subprocess.run(cmd, **kwargs).returncode
    except FileNotFoundError:
        return 127


def capture(cmd, stderr=subprocess.DEVNULL, timeout=None, stdin=subprocess.DEVNULL, **kwargs):
    """Run without input (unless `stdin` says otherwise); returns (exit code, stdout as text). A missing
    program or a timeout gives 127/124 and empty output, as the shell would. stderr=None shows errors."""
    if stderr is None:
        sys.stdout.flush()
        sys.stderr.flush()
    try:
        p = subprocess.run(cmd, stdin=stdin, stdout=subprocess.PIPE, stderr=stderr,
                           text=True, timeout=timeout, **kwargs)
        return p.returncode, p.stdout
    except FileNotFoundError:
        return 127, ""
    except subprocess.TimeoutExpired:
        return 124, ""


def succeeds(cmd, timeout=None, **kwargs):
    """Run without input or output; True if it exited 0."""
    try:
        return subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, timeout=timeout, **kwargs).returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def have(program):
    """`command -v program` for programs on PATH."""
    return shutil.which(program) is not None


def check(code, strict):
    """A command's exit code under the Bash version's set -e: when `strict` (set -e in force), a failure stops
    Torquio with that code, as it did; otherwise it's just returned."""
    if code != 0 and strict:
        raise SystemExit(code)
    return code
