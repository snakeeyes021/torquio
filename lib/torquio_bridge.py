"""How the Bash wrappers (scripts/install.sh, scripts/cleanup.sh) call into the torquio package: torquio_py in scripts/common.sh runs
`python3 lib/torquio_bridge.py COMMAND ...`.

A script rather than `python3 -m torquio`, because -m looks in the current directory first, so a stray
torquio.py wherever the user happens to run Torquio from would be imported instead.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from torquio.__main__ import run_main  # noqa: E402

run_main()
