"""Torquio's host side: the core (this package's modules) and the terminal interface (cli/, launch/). Ported from
Bash in v0.6.0 (docs/REFACTOR.md).

Standard library only. Keep everything here runnable on Python 3.9: no `match`, no `X | Y` unions outside
annotations (and only with `from __future__ import annotations`), nothing from 3.10+.
"""

MIN_PYTHON = (3, 9)


def _user_bin_on_path():
    """~/.local/bin first on PATH: Distrobox's user-level install puts it there (the app offers that install
    where the system mustn't change), and a desktop session started before it existed doesn't have it yet."""
    import os
    user_bin = os.path.join(os.path.expanduser("~"), ".local", "bin")
    parts = os.environ.get("PATH", "").split(os.pathsep)
    if os.path.isdir(user_bin) and user_bin not in parts:
        os.environ["PATH"] = os.pathsep.join([user_bin] + [p for p in parts if p])


_user_bin_on_path()
