"""Launcher logic against the Bash it replaces (the Download Assistant watcher's status file check)."""
import os
import shutil
import subprocess
import tempfile
import unittest

from torquio.launch import sda

# The watcher's test as of v0.5.0: prints "yes" when it would refresh the icons
BASH_CHECK = r'''
artifactId=$(grep -o '"artifactId":\s*"[^"]*"' "$1" | head -n 1 | cut -d'"' -f4)
success=$(grep -o '"success":\s*\(true\|false\)' "$1" | head -n 1 | cut -d':' -f2 | tr -d '[:space:]')
if [[ "$artifactId" =~ Dorico.*Application_Installer ]] && [ "$success" = "true" ]; then echo yes; else echo no; fi
'''
STATUS_FILES = [
    '{"artifactId": "Dorico_6_Application_Installer", "success": true}',
    '{"artifactId":"Dorico_6_Application_Installer","success":false}',
    '{\n  "artifactId": "Dorico 6 Application_Installer",\n  "success":   true\n}',
    '{"artifactId": "HALion_Sonic_Installer", "success": true}',
    '{"success": true, "artifactId": "Dorico_Application_Installer"}\n{"artifactId": "Other", "success": false}',
    '{"artifactId": "Dorico_6_Application_Installer"}',
    "",
]


@unittest.skipUnless(shutil.which("bash") and shutil.which("grep"), "needs bash and grep")
class WatcherMatchesBash(unittest.TestCase):
    def test_dorico_installed(self):
        for text in STATUS_FILES:
            with self.subTest(text=text), tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "status.json")
                with open(path, "w") as f:
                    f.write(text)
                expected = subprocess.run(["bash", "-c", BASH_CHECK, "bash", path], capture_output=True,
                                          text=True).stdout.strip() == "yes"
                self.assertEqual(sda.dorico_installed(path), expected)


if __name__ == "__main__":
    unittest.main()
