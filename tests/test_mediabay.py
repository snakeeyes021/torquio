"""The MediaBay update the Download Assistant couldn't install: the newest downloaded zip, only when it's newer
than the installed MediaBay and Torquio hasn't tried it already."""
import os
import tempfile
import unittest
import zipfile
from unittest import mock

from torquio import mediabay


def download(prefix, name, version):
    folder = os.path.join(prefix, "drive_c/users/u/AppData/Local/Temp", name)
    os.makedirs(folder)
    with zipfile.ZipFile(os.path.join(folder, mediabay.ZIP), "w") as z:
        z.writestr(f"MediaBay {version}/Setup.exe", "")
        z.writestr(f"MediaBay {version}/setup.xml", "")
    return folder


class FailedUpdate(unittest.TestCase):
    def find(self, installed, *downloads, tried=()):
        with tempfile.TemporaryDirectory() as prefix:
            for args in downloads:
                download(prefix, *args)
            for version in tried:
                open(os.path.join(prefix, f".torquio_mediabay_update_{version}"), "w").close()
            with mock.patch.object(mediabay.paths, "prefix_dir", return_value=prefix), \
                    mock.patch.object(mediabay, "installed_version", return_value=installed):
                found = mediabay.failed_update()
            return found and found[1]

    def test_newer_failed_download(self):
        self.assertEqual(self.find("1.3.80", ("a", "1.4.10")), "1.4.10")

    def test_newest_of_several(self):
        self.assertEqual(self.find("1.3.80", ("a", "1.4.2"), ("b", "1.4.10")), "1.4.10")

    def test_not_when_installed_is_as_new(self):
        self.assertFalse(self.find("1.4.10", ("a", "1.4.10")))

    def test_not_twice(self):
        self.assertFalse(self.find("1.3.80", ("a", "1.4.10"), tried=["1.4.10"]))

    def test_not_a_broken_zip(self):
        with tempfile.TemporaryDirectory() as prefix:
            folder = os.path.join(prefix, "drive_c/users/u/AppData/Local/Temp/a")
            os.makedirs(folder)
            with open(os.path.join(folder, mediabay.ZIP), "w") as f:
                f.write("partial download")
            with mock.patch.object(mediabay.paths, "prefix_dir", return_value=prefix), \
                    mock.patch.object(mediabay, "installed_version", return_value="1.3.80"):
                self.assertIsNone(mediabay.failed_update())


if __name__ == "__main__":
    unittest.main()
