"""Flows the parity harness compares. Each scenario:
    name           short identifier (run.py takes names to run a subset)
    args           arguments to ./torquio
    input          what the user types (all at once; echo is off, so it doesn't appear in the output)
    files          {path relative to $HOME: contents} created before the run
    compare_files  paths relative to $HOME whose contents must match afterwards
    timeout        seconds (default 120)

All of them run with nothing installed (the fakes report no container); stages that port the dashboard and
maintenance screens add scenarios with an installed-looking prefix.
"""
CONFIG = ".config/torquio/config.json"

SCENARIOS = [
    {"name": "unknown-flag", "args": ["--no-such-flag"]},
    {"name": "status", "args": ["--status"]},
    {"name": "menu-exit", "input": "7\n"},
    {"name": "menu-invalid", "input": "42\n\n7\n"},
    {"name": "menu-eof", "input": "\x04"},  # Ctrl+D at the menu prompt
    {"name": "settings-toggle", "input": "6\n1\n1\n2\n7\n", "compare_files": [CONFIG]},
    {"name": "settings-existing-config", "input": "6\n1\n2\n7\n", "compare_files": [CONFIG],
     "files": {CONFIG: '{\n    "manage_graphics": true,\n    "manual_dpi": 120,\n    "check_for_updates": false\n}'}},
    {"name": "settings-broken-config", "input": "6\n1\n2\n7\n", "compare_files": [CONFIG],
     "files": {CONFIG: "{not json"}},
    {"name": "manifest", "args": ["--manifest"]},
    {"name": "export-logs", "args": ["--export-logs"]},
    {"name": "uninstall-nothing-installed", "args": ["--uninstall"], "input": "n\n\n"},
]
