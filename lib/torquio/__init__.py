"""Torquio's host-side core, being ported from Bash (see docs/REFACTOR.md).

Standard library only. Keep everything here runnable on Python 3.9: no `match`, no `X | Y` unions outside
annotations (and only with `from __future__ import annotations`), nothing from 3.10+.
"""

MIN_PYTHON = (3, 9)
