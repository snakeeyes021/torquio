"""Torquio's settings file, ~/.config/torquio/config.json.

A flat JSON object. Values keep their JSON types (booleans stay booleans, numbers stay numbers), because
existing installs already have files written that way.
"""
import json
import os

from . import paths


def load(path=None):
    """The settings as a dict. Raises OSError/ValueError if the file is missing or unreadable."""
    with open(path or paths.config_file()) as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("config.json isn't a JSON object")
    return data


def get(key, default=None, path=None):
    """A setting's value, or `default` if it's not set (or the file is missing or unreadable)."""
    try:
        return load(path).get(key, default)
    except (OSError, ValueError):
        return default


def as_text(value):
    """A value as Bash's get_config_val prints it: booleans as true/false, everything else via str()."""
    return str(value).lower() if isinstance(value, bool) else str(value)


def get_text(key, default, path=None):
    """get_config_val: the setting as text, `default` (unchanged) if it's not set."""
    return as_text(get(key, default, path))


def from_text(text):
    """How set_config_val stores a value given as text: true/false (any case) as booleans, digits as ints."""
    if text.lower() == "true":
        return True
    if text.lower() == "false":
        return False
    if text.isdigit():
        return int(text)
    return text


def _create(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.isfile(path):
        with open(path, "w") as f:
            f.write("{}\n")


def set(key, value, path=None):  # noqa: A001 (mirrors set_config_val)
    """Store one setting. An unreadable file is replaced by one holding just this setting."""
    path = path or paths.config_file()
    _create(path)
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        data = {}
    data[key] = value
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


def set_text(key, text, path=None):
    """set_config_val: store a setting given as text (see from_text). The file is created first, as
    set_config_val did, even if the text then can't be converted (e.g. "²" counts as a digit)."""
    path = path or paths.config_file()
    _create(path)
    set(key, from_text(text), path)
