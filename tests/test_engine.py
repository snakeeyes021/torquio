"""engine.py against the Bash it replaces (engine_outdated's expected record, torquio_prebuilt_image)."""
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from torquio import engine, paths

REPO = paths.repo_dir()
WANTED = r'''
SCRIPT_DIR="$1"
echo "zhiyi_commit=$(sed -n 's/^TARGET_COMMIT="\(.*\)"$/\1/p' "$SCRIPT_DIR/scripts/1-build/build_wine.sh")"
for patch in "$SCRIPT_DIR"/scripts/1-build/patches/*.patch; do
    echo "patch=$(sha256sum "$patch" | cut -c1-12) $(basename "$patch" .patch)"
done'''


@unittest.skipUnless(shutil.which("bash") and shutil.which("sha256sum"), "needs bash and coreutils")
class EngineMatchesBash(unittest.TestCase):
    def test_wanted_build_record(self):
        out = subprocess.run(["bash", "-c", WANTED, "bash", REPO], capture_output=True, text=True, check=True).stdout
        self.assertEqual(engine.wanted_build_record(), out.rstrip("\n"))

    @unittest.skipUnless(os.path.isdir(os.path.join(REPO, ".git")) and shutil.which("git"), "needs a git checkout")
    def test_prebuilt_image(self):
        with tempfile.TemporaryDirectory() as home:
            for config in (None, '{"build_from_source": true}', '{"build_from_source": false}'):
                with self.subTest(config=config):
                    if config:
                        os.makedirs(os.path.join(home, ".config/torquio"), exist_ok=True)
                        with open(os.path.join(home, ".config/torquio/config.json"), "w") as f:
                            f.write(config)
                    env = {"HOME": home, "PATH": os.environ["PATH"]}
                    out = subprocess.run(["bash", "-c", 'source "$1/scripts/common.sh"; torquio_prebuilt_image',
                                          "bash", REPO], env=env, capture_output=True, text=True).stdout
                    with mock.patch.dict(os.environ, env, clear=True):
                        self.assertEqual(engine.prebuilt_image(), out.rstrip("\n"))


if __name__ == "__main__":
    unittest.main()
