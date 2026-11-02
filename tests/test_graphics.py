"""graphics.field against the grep -o | cut pipelines the Bash screens used, on the same JSON."""
import json
import shutil
import subprocess
import unittest

from torquio import graphics

SAMPLES = [
    json.dumps({"de": "GNOME", "supported": True, "connector": "DP-1", "width": 3840, "height": 2160, "scale": 1.33333,
                "physical_dpi": 161, "target_wine_dpi": 96, "rec_formula": "Formula: Standard 96 DPI baseline"}),
    json.dumps({"de": "KDE", "supported": False}),
    json.dumps({"de": "X", "width": None, "scale": 2, "connector": ""}),
    '{"width": 1920, "width": 2560, "scale": 1.0}',  # repeated key: every match, one per line
    "",
]
PIPELINES = {  # (key, kind): the Bash pipeline
    ("de", "string"): """grep -o '"de": "[^"]*' | cut -d'"' -f4""",
    ("connector", "string"): """grep -o '"connector": "[^"]*' | cut -d'"' -f4""",
    ("rec_formula", "string"): """grep -o '"rec_formula": "[^"]*' | cut -d'"' -f4""",
    ("scale", "number"): """grep -o '"scale": [0-9.]*' | cut -d' ' -f2""",
    ("width", "int"): """grep -o '"width": [0-9]*' | cut -d' ' -f2""",
    ("height", "int"): """grep -o '"height": [0-9]*' | cut -d' ' -f2""",
    ("target_wine_dpi", "int"): """grep -o '"target_wine_dpi": [0-9]*' | cut -d' ' -f2""",
}


@unittest.skipUnless(shutil.which("bash"), "needs bash")
class FieldsMatchGrep(unittest.TestCase):
    def test_fields(self):
        for sample in SAMPLES:
            for (key, kind), pipeline in PIPELINES.items():
                with self.subTest(sample=sample, key=key):
                    out = subprocess.run(["bash", "-c", f'echo "$1" | {pipeline}', "bash", sample],
                                         capture_output=True, text=True).stdout.rstrip("\n")
                    self.assertEqual(graphics.field(sample, key, kind), out)

    def test_scale_percent(self):
        for scale, expected in [("1.33333", "133"), ("2", "200"), ("1.25", "125"), ("", "100"), ("1.2.3", "100"),
                                ("1.0\n1.5", "100")]:
            code = subprocess.run(["python3", "-c", f"print(int(round({scale} * 100)))"], capture_output=True, text=True)
            self.assertEqual(graphics.scale_percent(scale), code.stdout.strip() if code.returncode == 0 else "100")
            self.assertEqual(graphics.scale_percent(scale), expected)


if __name__ == "__main__":
    unittest.main()


def _graphics_script():
    import importlib.util
    import os
    path = os.path.join(os.path.dirname(__file__), "..", "scripts/3-runtime_handlers/torquio_graphics.py")
    spec = importlib.util.spec_from_file_location("torquio_graphics", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# kscreen-doctor -o from Plasma 6 (Fedora 44): coloured even into a pipe, Geometry is the scaled size, and the
# current mode isn't the first one listed
KSCREEN = ("\x1b[01;32mOutput: \x1b[0;0m1 Virtual-1 84ab7432\n\t\x1b[01;32menabled\x1b[0;0m\n"
           "\t\x1b[01;32mpriority 1\x1b[0;0m\n"
           "\t\x1b[01;34mModes: \x1b[0;0m 1:1280x800@74.99!  2:\x1b[01;32m1920x1080@60.00*\x1b[0;0m  3:640x480@60.00\n"
           "\x1b[01;33m\tGeometry: \x1b[0;0m0,0 1536x864\n\x1b[01;33m\tScale: \x1b[0;0m1.25\n")


class KdeQuery(unittest.TestCase):
    def test_coloured_kscreen_doctor(self):
        from unittest import mock
        script = _graphics_script()
        with mock.patch.object(script, "run_cmd", return_value=KSCREEN), \
                mock.patch.object(script, "get_edid_dpi", return_value=96), \
                mock.patch.object(script, "should_match_physical_dpi", return_value=False):
            data = script.query_kde()
        self.assertEqual((data["connector"], data["width"], data["height"], data["scale"]),
                         ("Virtual-1", 1920, 1080, 1.25))
        self.assertEqual(data["target_wine_dpi"], 120)
