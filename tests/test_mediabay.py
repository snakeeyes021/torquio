"""The MediaBay update the Download Assistant couldn't install: found only when it failed with error 231 and is
newer than the installed MediaBay."""
import json
import os
import tempfile
import unittest
import zipfile
from unittest import mock

from torquio import mediabay


def download(prefix, name, version, success=False, code="231"):
    folder = os.path.join(prefix, "drive_c/users/u/AppData/Local/Temp", name)
    os.makedirs(folder)
    with zipfile.ZipFile(os.path.join(folder, mediabay.ZIP), "w") as z:
        z.writestr(f"MediaBay {version}/Setup.exe", "")
        z.writestr(f"MediaBay {version}/setup.xml", "")
    with open(os.path.join(folder, mediabay.STATUS), "w") as f:
        json.dump({"artifactId": "Steinberg_MediaBay_Installer", "success": success,
                   "errors": [] if success else [{"code": code, "message": "preinstall.ps1: not trusted."}]}, f)
    return folder


class FailedUpdate(unittest.TestCase):
    def find(self, installed, *downloads):
        with tempfile.TemporaryDirectory() as prefix:
            for args in downloads:
                download(prefix, *args)
            with mock.patch.object(mediabay.paths, "prefix_dir", return_value=prefix), \
                    mock.patch.object(mediabay, "installed_version", return_value=installed):
                found = mediabay.failed_update()
            return found and found[2]

    def test_newer_failed_download(self):
        self.assertEqual(self.find("1.3.80", ("a", "1.4.10")), "1.4.10")

    def test_newest_of_several(self):
        self.assertEqual(self.find("1.3.80", ("a", "1.4.2"), ("b", "1.4.10")), "1.4.10")

    def test_not_when_installed_is_as_new(self):
        self.assertFalse(self.find("1.4.10", ("a", "1.4.10")))

    def test_not_other_failures_or_successes(self):
        self.assertFalse(self.find("1.3.80", ("a", "1.4.10", True)))
        self.assertFalse(self.find("1.3.80", ("a", "1.4.10", False, "1603")))


if __name__ == "__main__":
    unittest.main()
