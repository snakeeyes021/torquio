"""Torquio's host side: the core (this package's modules) and the terminal interface (cli/, launch/). Ported from
Bash in v0.6.0 (docs/REFACTOR.md).

Standard library only. Keep everything here runnable on Python 3.9: no `match`, no `X | Y` unions outside
annotations (and only with `from __future__ import annotations`), nothing from 3.10+.
"""

MIN_PYTHON = (3, 9)
