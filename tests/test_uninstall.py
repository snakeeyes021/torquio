"""uninstall.py against the find and sed commands the Bash uninstaller used (v0.5.0)."""
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from torquio import uninstall

FIND_PROJECTS = r'''find "$1/drive_c" \( -path "*/Program Files*" -o -path "*/ProgramData" \
    -o -path "*/windows" -o -path "*/AppData" -o -path "*/users/Public/Documents/Dorico Example Projects" \) -prune \
    -o -type f -iname '*.dorico' -print 2>/dev/null'''
SED_MIMEAPPS = r'''sed -i -E '/^[^=]+=(Dorico|Steinberg Download Assistant|Steinberg Activation Manager|Dorico Audio Engine)\.desktop;?$/d' "$1"'''

TREE = [
    "drive_c/users/me/Documents/a.dorico", "drive_c/users/me/Documents/Sub/b.DORICO", "drive_c/users/me/c.Dorico",
    "drive_c/users/me/AppData/Roaming/x.dorico", "drive_c/Program Files/Steinberg/t.dorico",
    "drive_c/Program Files (x86)/y.dorico", "drive_c/ProgramData/z.dorico", "drive_c/ProgramData2/keep.dorico",
    "drive_c/windows/w.dorico", "drive_c/users/Public/Documents/Dorico Example Projects/e.dorico",
    "drive_c/users/Public/Documents/Mine/m.dorico", "drive_c/users/me/notes.txt", "drive_c/users/me/My Program Files/p.dorico",
    "drive_c/users/me/dir.dorico/inner.txt",
]
MIMEAPPS = [
    "[Default Applications]\napplication/x-dorico=Dorico.desktop;\ntext/plain=gedit.desktop\n",
    "x-scheme-handler/a=Steinberg Activation Manager.desktop\nx=Dorico Audio Engine.desktop\ny=Dorico.desktop;other.desktop\n",
    "no newline at the end=Dorico.desktop",
    "=Dorico.desktop\nkey=Dorico.desktop;;\n",
]


@unittest.skipUnless(shutil.which("find") and shutil.which("sed") and shutil.which("bash"), "needs find, sed, bash")
class UninstallMatchesBash(unittest.TestCase):
    def test_prefix_projects(self):
        with tempfile.TemporaryDirectory() as home:
            prefix = os.path.join(home, ".local/share/torquio/prefix")
            for rel in TREE:
                os.makedirs(os.path.dirname(os.path.join(prefix, rel)), exist_ok=True)
                open(os.path.join(prefix, rel), "w").close()
            os.symlink(os.path.join(home, "outside"), os.path.join(prefix, "drive_c/users/me/Music"))
            os.makedirs(os.path.join(home, "outside"))
            open(os.path.join(home, "outside/linked.dorico"), "w").close()
            expected = subprocess.run(["bash", "-c", FIND_PROJECTS, "bash", prefix], capture_output=True,
                                      text=True).stdout.splitlines()
            with mock.patch.dict(os.environ, {"HOME": home, "XDG_DATA_HOME": ""}):
                self.assertEqual(uninstall.prefix_projects(), expected)

    def test_remove_default_apps(self):
        for text in MIMEAPPS:
            with self.subTest(text=text), tempfile.TemporaryDirectory() as tmp:
                ours, theirs = os.path.join(tmp, "ours"), os.path.join(tmp, "theirs")
                for path in (ours, theirs):
                    with open(path, "w") as f:
                        f.write(text)
                subprocess.run(["bash", "-c", SED_MIMEAPPS, "bash", theirs], check=True)
                uninstall.remove_default_apps(ours)
                with open(ours, "rb") as a, open(theirs, "rb") as b:
                    self.assertEqual(a.read(), b.read())


if __name__ == "__main__":
    unittest.main()
