"""engine.py against the Bash it replaces (engine_outdated's expected record, torquio_prebuilt_image)."""
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from torquio import engine, paths

REPO = paths.repo_dir()
# torquio_prebuilt_image and get_config_val as of v0.5.0 (scripts/common.sh)
OLD_PREBUILT_IMAGE = r'''
TORQUIO_REPO_DIR="$1"; TORQUIO_IMAGE_REPO="${TORQUIO_IMAGE_REPO:-ghcr.io/snakeeyes021/torquio-env}"
get_config_val() {
    local key="$1" default="$2" config_file="$HOME/.config/torquio/config.json"
    if [ ! -f "$config_file" ]; then echo "$default"; return; fi
    python3 -c 'import sys, json; d=json.load(open(sys.argv[1])); v=d.get(sys.argv[2], sys.argv[3]); print(str(v).lower() if isinstance(v, bool) else v)' "$config_file" "$key" "$default" 2>/dev/null || echo "$default"
}
torquio_prebuilt_image() {
    [ "$(get_config_val "build_from_source" "false")" = "true" ] && return
    [ -z "$(git -C "$TORQUIO_REPO_DIR" status --porcelain -- scripts/1-build 2>/dev/null)" ] || return 0
    local tree
    tree=$(git -C "$TORQUIO_REPO_DIR" rev-parse HEAD:scripts/1-build 2>/dev/null) || return 0
    echo "$TORQUIO_IMAGE_REPO:build-${tree:0:12}"
}
torquio_prebuilt_image
'''
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
                    out = subprocess.run(["bash", "-c", OLD_PREBUILT_IMAGE, "bash", REPO], env=env,
                                         capture_output=True, text=True).stdout
                    with mock.patch.dict(os.environ, env, clear=True):
                        self.assertEqual(engine.prebuilt_image(), out.rstrip("\n"))


if __name__ == "__main__":
    unittest.main()
