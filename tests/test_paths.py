"""paths.py against the variables scripts/common.sh sets, in the same environments."""
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from torquio import paths

REPO = paths.repo_dir()
SHOW = ('source "$1/scripts/common.sh"; printf "%s\\n" "$TORQUIO_CONTAINER_NAME" "$TORQUIO_DATA_DIR" '
        '"$TORQUIO_CACHE_DIR" "$TORQUIO_PREFIX_DIR" "$TORQUIO_BUILD_DIR" "$TORQUIO_INSTALLERS_DIR" '
        '"$TORQUIO_IMAGE_REPO" "$TORQUIO_REPO_DIR"')


@unittest.skipUnless(shutil.which("bash"), "needs bash")
class PathsMatchCommonSh(unittest.TestCase):
    def test_environments(self):
        with tempfile.TemporaryDirectory() as home:
            base = {"HOME": home, "PATH": os.environ.get("PATH", "/usr/bin:/bin")}
            environments = [
                {},
                {"XDG_DATA_HOME": os.path.join(home, "data"), "XDG_CACHE_HOME": os.path.join(home, "cache")},
                {"XDG_DATA_HOME": "", "XDG_CACHE_HOME": ""},  # empty counts as unset
                {"TORQUIO_CONTAINER_NAME": "torquio-test", "TORQUIO_IMAGE_REPO": "localhost/torquio"},
                {"TORQUIO_CONTAINER_NAME": ""},
            ]
            for extra in environments:
                env = dict(base, **extra)
                with self.subTest(env=extra):
                    out = subprocess.run(["bash", "-c", SHOW, "bash", REPO], env=env, capture_output=True,
                                         text=True, check=True).stdout.splitlines()
                    with mock.patch.dict(os.environ, env, clear=True):
                        ours = [paths.container_name(), paths.data_dir(), paths.cache_dir(), paths.prefix_dir(),
                                paths.build_dir(), paths.installers_dir(), paths.image_repo(), paths.repo_dir()]
                    self.assertEqual(ours, out)

    def test_config_file_ignores_xdg_config_home(self):
        with mock.patch.dict(os.environ, {"HOME": "/home/u", "XDG_CONFIG_HOME": "/elsewhere"}):
            self.assertEqual(paths.config_file(), "/home/u/.config/torquio/config.json")


if __name__ == "__main__":
    unittest.main()
