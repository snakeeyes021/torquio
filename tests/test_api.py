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


class VerbArguments(unittest.TestCase):
    """Verbs get their arguments as a tuple (`VERBS[verb](*args)`), through `api.main` as the GUI calls them."""

    def call(self, *args):
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            code = api.main(list(args))
        return code, json.loads(out.getvalue())

    def test_folders_map_reaches_the_check(self):
        code, data = self.call("folders", "map", "/nonexistent-torquio-test", "drive")
        self.assertEqual((code, data["error"]), (1, "That folder doesn't exist."))

    def test_keycommands_import_reaches_the_check(self):
        code, data = self.call("keycommands", "import", "/nonexistent-torquio-test.zip")
        self.assertEqual((code, data["error"]), (1, "Choose a key commands backup (.zip or .json)."))

    def test_display_restore_restores(self):
        with mock.patch.object(api, "restore_desktop_scaling") as restore, \
                mock.patch.object(api.graphics, "query", return_value=""), \
                mock.patch.object(api.graphics, "wine_prefix_dpi", return_value="96"), \
                mock.patch.object(api, "_restorable", return_value=None):
            code, _data = self.call("display", "restore")
        self.assertEqual(code, 0)
        restore.assert_called_once()

    def test_updates_check_fetches(self):
        with mock.patch.object(api.run, "succeeds", return_value=True) as succeeds, \
                mock.patch.object(api.run, "capture", return_value=(0, "")):
            code, data = self.call("updates", "check")
        self.assertEqual(code, 0)
        self.assertTrue(any("fetch" in call.args[0] for call in succeeds.call_args_list))

    def test_updates_daily_uses_the_daily_check(self):
        from torquio.cli import tools
        with mock.patch.object(tools, "check_for_updates") as daily, \
                mock.patch.object(api.run, "succeeds", return_value=False), \
                mock.patch.object(api.run, "capture", return_value=(0, "")):
            code, _data = self.call("updates", "daily")
        self.assertEqual(code, 0)
        daily.assert_called_once()


class Tasks(unittest.TestCase):
    def test_one_task_at_a_time(self):
        import tempfile
        with tempfile.TemporaryDirectory() as cache, mock.patch.object(api.paths, "cache_dir", return_value=cache):
            first = api._task_lock()
            self.assertIsNotNone(first)
            self.assertIsNone(api._task_lock())
            first.close()
            again = api._task_lock()
            self.assertIsNotNone(again)
            again.close()

    def test_events_stop_quietly_when_the_gui_is_gone(self):
        class Gone(io.StringIO):
            def write(self, text):
                raise BrokenPipeError()
        with mock.patch("sys.stdout", Gone()), mock.patch.object(api.os, "dup2"):
            api._emit("log", text="one")  # doesn't raise
            self.assertTrue(api._Events.gone)
            api._emit("log", text="two")
        api._Events.gone = False
