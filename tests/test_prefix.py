"""prefix.py's container scripts against the strings the Bash version built (v0.5.0)."""
import os
import shutil
import subprocess
import unittest
from unittest import mock

from torquio import prefix

# apply_prefix_settings as of v0.5.0, printing the script instead of running it
APPLY_PREFIX_SETTINGS = r'''
TORQUIO_PREFIX_DIR="$1"; WINE_CUSTOM_BIN=/opt/wine-custom/bin
printf '%s' "export WINEPREFIX=\"$TORQUIO_PREFIX_DIR\"; export PATH=\"$WINE_CUSTOM_BIN:\$PATH\"; export WINEDEBUG=-all
        wine reg add 'HKCU\\Software\\Wine\\Fonts\\Replacements' /v 'Segoe UI' /t REG_SZ /d Tahoma /f
        wine reg add 'HKCU\\Software\\Wine\\AppDefaults\\rundll32.exe\\DllOverrides' /v '*mscoree' /t REG_SZ /d '' /f
        wineserver -w"
'''


@unittest.skipUnless(shutil.which("bash"), "needs bash")
class PrefixScriptsMatchBash(unittest.TestCase):
    def test_apply_settings(self):
        home = "/home/someone"
        expected = subprocess.run(["bash", "-c", APPLY_PREFIX_SETTINGS, "bash", f"{home}/.local/share/torquio/prefix"],
                                  capture_output=True, text=True, check=True).stdout
        calls = []
        with mock.patch.dict(os.environ, {"HOME": home, "XDG_DATA_HOME": ""}), \
                mock.patch.object(prefix.os.path, "isfile", return_value=True), \
                mock.patch.object(prefix.run, "interactive", side_effect=lambda cmd, **kw: calls.append(cmd)):
            prefix.apply_settings()
        self.assertEqual(calls, [["distrobox", "enter", "torquio-env", "--", "bash", "-c", expected]])


if __name__ == "__main__":
    unittest.main()
