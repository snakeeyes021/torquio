"""`torquio api`: JSON only, and an error (exit code 2) for unknown verbs."""
import io
import json
import unittest
from unittest import mock

from torquio import api


class Api(unittest.TestCase):
    def test_unknown_verb(self):
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            self.assertEqual(api.main(["nope"]), 2)
        self.assertIn("version", json.loads(out.getvalue())["verbs"])

    def test_version(self):
        out = io.StringIO()
        with mock.patch.object(api.run, "capture", return_value=(0, "v0.7.0-alpha\n")), \
                mock.patch("sys.stdout", out):
            self.assertEqual(api.main(["version"]), 0)
        self.assertEqual(json.loads(out.getvalue())["torquio"], "v0.7.0-alpha")
        self.assertEqual(json.loads(out.getvalue())["api"], api.API_VERSION)


if __name__ == "__main__":
    unittest.main()


class Settings(unittest.TestCase):
    def test_refuses_bad_values(self):
        for args in (("set", "nope", "1"), ("set", "manual_dpi", "abc"), ("set", "manual_dpi", "9999"),
                     ("set", "manage_graphics", "yes"), ("set", "freetype_interpreter", "38"), ("get",)):
            with self.subTest(args=args), mock.patch.object(api.config, "set_text") as set_text:
                with self.assertRaises(api.Error):
                    api.settings(*args)
                set_text.assert_not_called()

    def test_graphics_settings_are_applied(self):
        with mock.patch.object(api.config, "set_text") as set_text, \
                mock.patch.object(api.config, "get_text", side_effect=lambda k, d, path=None: d), \
                mock.patch.object(api.graphics, "apply_settings") as apply:
            api.settings("set", "manual_dpi", "120")
            api.settings("set", "ai_gpu", "off")
        set_text.assert_any_call("manual_dpi", "120")
        self.assertEqual(apply.call_count, 1)  # ai_gpu doesn't restart Wine


class TaskSteps(unittest.TestCase):
    def test_friendly_names(self):
        self.assertIsNone(api.phase_name("Installation Manifest"))
        self.assertEqual(api.phase_name("Wine Engine..."), "Getting the Wine engine")
        self.assertEqual(api.phase_name("Something new..."), "Something new")
