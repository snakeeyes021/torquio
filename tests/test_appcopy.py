"""The app's copy of Torquio in ~/.local/share/torquio/app: uninstalling keeps it (it may be the code doing the
uninstall) until the very last step, and only when the app is being removed too."""
import os
import tempfile
import unittest
from unittest import mock

from torquio import paths, uninstall


class AppCopy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        home = self.tmp.name
        self.data = os.path.join(home, ".local/share/torquio")
        for sub in ("prefix/drive_c", "app/lib", "logs"):
            os.makedirs(os.path.join(self.data, sub))
        os.makedirs(os.path.join(home, ".cache/torquio"))
        patches = [mock.patch.object(paths, "home", return_value=home),
                   mock.patch.object(paths, "data_dir", return_value=self.data),
                   mock.patch.object(paths, "cache_dir", return_value=os.path.join(home, ".cache/torquio"))]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def test_uninstalling_keeps_the_app_copy(self):
        uninstall.remove_data()
        self.assertEqual(os.listdir(self.data), ["app"])
        self.assertTrue(os.path.isdir(os.path.join(self.data, "app/lib")))

    def test_the_last_step_removes_it_and_the_folder(self):
        uninstall.remove_data()
        uninstall.remove_app_copy()
        self.assertFalse(os.path.exists(self.data))

    def test_app_dir_is_in_the_data_folder(self):
        self.assertEqual(paths.app_dir(), os.path.join(self.data, "app"))


if __name__ == "__main__":
    unittest.main()
