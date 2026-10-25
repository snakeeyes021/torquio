"""versions.sort against GNU sort -V."""
import shutil
import subprocess
import unittest

from torquio import versions

NAMES = ["2.9", "2.14.1", "2.13", "2.14", "2.14.0", "v2.10", "v2.9", "2.14.1-rc1", "2.14.1~rc1", "10", "9.9.9",
         "2.014", "2.14a", "2.14b", "a", "B", "1.0.0", "1.0", "1", "1-2", "1.2-3", "", "_x", "2.14.1/", "0.9"]


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
