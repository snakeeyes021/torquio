"""config.py against the Python one-liners scripts/common.sh used before (v0.5.0), on the same files."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

from torquio import config

# get_config_val and set_config_val as of v0.5.0 (the bash wrappers' parts are replayed in the helpers below)
OLD_GET = ('import sys, json; d=json.load(open(sys.argv[1])); v=d.get(sys.argv[2], sys.argv[3]); '
           'print(str(v).lower() if isinstance(v, bool) else v)')
OLD_SET = '''
import sys, json
f = sys.argv[1]
key = sys.argv[2]
val = sys.argv[3]
try:
    d = json.load(open(f))
except Exception:
    d = {}
if val.lower() == "true":
    val = True
elif val.lower() == "false":
    val = False
elif val.isdigit():
    val = int(val)
d[key] = val
json.dump(d, open(f, "w"), indent=4)
'''

FILES = {
    "settings": json.dumps({"manage_graphics": True, "check_for_updates": False, "manual_dpi": 120, "scale": 1.5,
                            "nothing": None, "ai_gpu": "NVIDIA GeForce RTX 4060", "empty": "", "list": [1, 2]}, indent=4),
    "empty object": "{}\n",
    "not json": "{oops",
    "a list": "[1, 2]",
    "empty file": "",
    "unicode": json.dumps({"name": "Dorico Pro é"}),
}


def old_get(path, key, default):
    if not os.path.isfile(path):
        return default + "\n"
    p = subprocess.run([sys.executable, "-c", OLD_GET, path, key, default], capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else default + "\n"


def old_set(path, key, val):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.isfile(path):
        with open(path, "w") as f:
            f.write("{}\n")
    subprocess.run([sys.executable, "-c", OLD_SET, path, key, val], capture_output=True)


def new_get(path, key, default):
    return config.get_text(key, default, path) + "\n"


def new_set(path, key, val):
    try:
        config.set_text(key, val, path)
    except Exception:
        pass  # set_config_val ignores failures


class ConfigMatchesOldBash(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def path(self, name, contents=None):
        path = os.path.join(self.tmp.name, name, "config.json")
        if contents is not None:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(contents)
        return path

    def test_get(self):
        keys = ["manage_graphics", "check_for_updates", "manual_dpi", "scale", "nothing", "ai_gpu", "empty", "list",
                "name", "missing"]
        for label, contents in list(FILES.items()) + [("no file", None)]:
            path = self.path(label.replace(" ", "_"), contents)
            for key in keys:
                for default in ["false", "96", "", "auto"]:
                    with self.subTest(file=label, key=key, default=default):
                        self.assertEqual(new_get(path, key, default), old_get(path, key, default))

    def test_set(self):
        values = ["true", "FALSE", "True", "42", "0", "007", "-1", "1.5", "", "auto", "NVIDIA GeForce RTX 4060",
                  "²", "café"]
        for label, contents in list(FILES.items()) + [("no file", None)]:
            for i, value in enumerate(values):
                with self.subTest(file=label, value=value):
                    old = self.path(f"old{i}_{label.replace(' ', '_')}", contents)
                    new = self.path(f"new{i}_{label.replace(' ', '_')}", contents)
                    old_set(old, "key", value)
                    new_set(new, "key", value)
                    with open(old, "rb") as a, open(new, "rb") as b:
                        self.assertEqual(b.read(), a.read())

    def test_typed_values(self):
        path = self.path("typed")
        config.set("manage_graphics", True, path)
        config.set("manual_dpi", 120, path)
        self.assertIs(config.get("manage_graphics", path=path), True)
        self.assertEqual(config.get("manual_dpi", path=path), 120)
        self.assertEqual(config.get("missing", "x", path=path), "x")
        self.assertEqual(config.get_text("manage_graphics", "false", path), "true")


if __name__ == "__main__":
    unittest.main()
