"""Where Torquio keeps things (the same locations as scripts/common.sh).

Functions rather than constants, so they follow the environment they're called in (tests set their own).
Like Bash's ${VAR:-default}, an empty variable counts as unset.
"""
import os

WINE_CUSTOM_PATH = "/opt/wine-custom"
WINE_CUSTOM_BIN = WINE_CUSTOM_PATH + "/bin"
DEFAULT_CONTAINER_NAME = "torquio-env"
DEFAULT_IMAGE_REPO = "ghcr.io/snakeeyes021/torquio-env"


def _env(name, default):
    return os.environ.get(name) or default


def home():
    return _env("HOME", os.path.expanduser("~"))


def repo_dir():
    """The Torquio checkout this package belongs to (lib/torquio/ -> repo)."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def container_name():
    return _env("TORQUIO_CONTAINER_NAME", DEFAULT_CONTAINER_NAME)


def image_repo():
    return _env("TORQUIO_IMAGE_REPO", DEFAULT_IMAGE_REPO)


def data_dir():
    return os.path.join(_env("XDG_DATA_HOME", os.path.join(home(), ".local/share")), "torquio")


def cache_dir():
    return os.path.join(_env("XDG_CACHE_HOME", os.path.join(home(), ".cache")), "torquio")


def prefix_dir():
    return os.path.join(data_dir(), "prefix")


def build_dir():
    return os.path.join(cache_dir(), "wine-build")


def log_dir():
    return os.path.join(data_dir(), "logs")


def installers_dir():
    return os.path.join(repo_dir(), "installers")


def config_file():
    # Always under $HOME/.config, whatever XDG_CONFIG_HOME says (as in every release so far)
    return os.path.join(home(), ".config/torquio/config.json")
