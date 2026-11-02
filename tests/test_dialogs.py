"""Launcher dialogs: the fallback order (zenity, kdialog, GTK, notification), and that Wine is never restarted
under a running Dorico without an answer."""
import os
import subprocess
import sys
import unittest
from unittest import mock

from torquio import dialogs
from torquio.launch import common


def tools(*available):
    return lambda program: program in available


class Question(unittest.TestCase):
    def test_zenity_first(self):
        with mock.patch.object(dialogs.run, "have", tools("zenity", "kdialog")), \
                mock.patch.object(dialogs.run, "interactive", return_value=0) as interactive:
            self.assertIs(dialogs.question("Text", "Title"), True)
        self.assertEqual(interactive.call_args[0][0][0], "zenity")

    def test_gtk_without_zenity_or_kdialog(self):
        with mock.patch.object(dialogs.run, "have", tools()), \
                mock.patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}), \
                mock.patch.object(dialogs.run, "interactive", return_value=1) as interactive:
            self.assertIs(dialogs.question("Text", "Title"), False)
        self.assertEqual(interactive.call_args[0][0][:3], [sys.executable, "-I", dialogs.GTK_DIALOG])

    def test_none_when_gtk_is_unavailable(self):
        with mock.patch.object(dialogs.run, "have", tools()), \
                mock.patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}), \
                mock.patch.object(dialogs.run, "interactive", return_value=2):
            self.assertIsNone(dialogs.question("Text", "Title"))

    def test_none_without_a_display(self):
        env = {k: v for k, v in os.environ.items() if k not in ("WAYLAND_DISPLAY", "DISPLAY")}
        with mock.patch.object(dialogs.run, "have", tools()), mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(dialogs.run, "interactive") as interactive:
            self.assertIsNone(dialogs.question("Text", "Title"))
        interactive.assert_not_called()


class Message(unittest.TestCase):
    def test_notification_when_no_dialog_can_be_shown(self):
        with mock.patch.object(dialogs.run, "have", tools()), \
                mock.patch.object(dialogs, "_gtk", return_value=None), \
                mock.patch.object(dialogs, "notify", return_value=True) as notify:
            self.assertTrue(dialogs.message("warning", "Text", "Title"))
        notify.assert_called_once()


class GtkScript(unittest.TestCase):
    def test_wrong_arguments_mean_unavailable(self):
        p = subprocess.run([sys.executable, "-I", dialogs.GTK_DIALOG, "nonsense"], capture_output=True)
        self.assertEqual(p.returncode, 2)


class RestartWithoutAnswer(unittest.TestCase):
    """The display scale changed while Dorico runs: Wine is restarted only when the user says yes."""

    def manage(self, answer):
        status = '{"de": "KDE", "target_wine_dpi": 120, "scale": 1.25}'
        with mock.patch.object(common.graphics, "query_status", return_value=(0, status)), \
                mock.patch.object(common.graphics, "supported", return_value=True), \
                mock.patch.object(common.graphics, "kde_xwayland_policy", return_value="true"), \
                mock.patch.object(common.config, "get_text", side_effect=lambda key, default, path=None:
                                  "true" if key == "manage_graphics" else default), \
                mock.patch.object(common, "wine_dpi", return_value="96"), \
                mock.patch.object(common, "apps_running", return_value=True), \
                mock.patch.object(common.dialogs, "question", return_value=answer), \
                mock.patch.object(common.dialogs, "notify") as notify, \
                mock.patch.object(common.prefix, "set_dpi"), \
                mock.patch.object(common.prefix, "restart_wineserver") as restart, \
                mock.patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            common.manage_graphics(restartable=True)
        return restart.called, notify.called

    def test_yes_restarts(self):
        self.assertEqual(self.manage(True), (True, False))

    def test_no_leaves_wine_running(self):
        self.assertEqual(self.manage(False), (False, False))

    def test_no_way_to_ask_leaves_wine_running_and_says_so(self):
        self.assertEqual(self.manage(None), (False, True))


if __name__ == "__main__":
    unittest.main()
