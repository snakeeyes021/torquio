"""versions.sort against GNU sort -V."""
import shutil
import subprocess
import unittest

from torquio import versions

NAMES = ["2.9", "2.14.1", "2.13", "2.14", "2.14.0", "v2.10", "v2.9", "2.14.1-rc1", "2.14.1~rc1", "10", "9.9.9",
         "2.014", "2.14a", "2.14b", "a", "B", "1.0.0", "1.0", "1", "1-2", "1.2-3", "", "_x", "2.14.1/", "0.9",
         # file suffixes (sort -V compares names without them first) and hidden files
         "MediaBay_Installer_win64_1.4.10.zip", "MediaBay_Installer_win64_1.3.80.zip", "MediaBay_Installer_win64.zip",
         "Steinberg_Download_Assistant_1.39.2_Installer_win.exe", "Steinberg_Download_Assistant_1.4.0_Installer_win.exe",
         "Cantai-Windows-3.1.1-Installer-x64.exe.zip", "Cantai-Windows-3.10.0-Installer-x64.exe.zip",
         "a.tar.gz", "a.tar", "a1.tar.gz", "a1.b2.zip", "x.~1", ".hidden", ".hidden2", "file.txt~", "abc.1.2", "abc.1.10"]


@unittest.skipUnless(shutil.which("sort"), "needs sort")
class SortMatchesGnu(unittest.TestCase):
    def test_sort(self):
        names = [n for n in NAMES if n]
        expected = subprocess.run(["sort", "-V"], input="\n".join(names) + "\n", capture_output=True, text=True,
                                  env={"LC_ALL": "C"}).stdout.splitlines()
        self.assertEqual(versions.sort(names), expected)

    def test_paths(self):
        paths = [f"/home/me/.local/share/torquio/vkd3d-proton/{v}/" for v in ("2.9", "2.14.1", "2.13", "2.10.1")]
        expected = subprocess.run(["sort", "-V"], input="\n".join(paths) + "\n", capture_output=True, text=True,
                                  env={"LC_ALL": "C"}).stdout.splitlines()
        self.assertEqual(versions.sort(paths), expected)


if __name__ == "__main__":
    unittest.main()
