"""Torquio's stand-in for Windows PowerShell's hosting library (scripts/2-install/powershell_host): it has to carry
the identity Steinberg's Install Assistant references and the members it calls, or the installer can't load it."""
import base64
import hashlib
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "scripts/2-install/install_powershell_host.sh")
SOURCE = os.path.join(REPO, "scripts/2-install/powershell_host/System.Management.Automation.cs")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class Identity(unittest.TestCase):
    def test_public_key_token(self):
        key = base64.b64decode(re.search(r'^PUBLIC_KEY="([^"]+)"', read(SCRIPT), re.M).group(1))
        # The token is the last 8 bytes of the key's SHA-1, reversed
        self.assertEqual(hashlib.sha1(key).digest()[-8:][::-1].hex(), "31bf3856ad364e35")

    def test_version_and_tag(self):
        source = read(SOURCE)
        self.assertIn('[assembly: AssemblyVersion("3.0.0.0")]', source)
        tag = re.search(r'^TAG="([^"]+)"', read(SCRIPT), re.M).group(1)
        self.assertRegex(source, r'AssemblyInformationalVersion\("' + re.escape(tag))

    def test_gac_folder_matches(self):
        self.assertIn("GAC_MSIL/$NAME/v4.0_3.0.0.0__31bf3856ad364e35", read(SCRIPT))


class Members(unittest.TestCase):
    """What Steinberg's Setup.exe (Install Assistant, the same build in MediaBay 1.3.70 to 1.4.10) calls."""
    def test_members_the_installer_calls(self):
        source = " ".join(read(SOURCE).split())
        for member in (
            "namespace System.Management.Automation",
            "public sealed class PowerShell : IDisposable",
            "public static PowerShell Create()",
            "public PowerShell AddScript(string script)",
            "public PowerShell AddParameters(IList parameters)",
            "public Collection<PSObject> Invoke()",
            "public PSDataStreams Streams",
            "public void Dispose()",
            "public PSDataCollection<InformationRecord> Information",
            "public PSDataCollection<WarningRecord> Warning",
            "public PSDataCollection<ErrorRecord> Error",
            "public IEnumerator<T> GetEnumerator()",
            "public class PSObject",
            "public class InformationRecord",
            "public class WarningRecord",
            "public class ErrorRecord",
        ):
            self.assertIn(member, source)

    def test_setup_prefix_installs_it(self):
        self.assertIn("install_powershell_host.sh", read(os.path.join(REPO, "scripts/2-install/setup_prefix.sh")))


if __name__ == "__main__":
    unittest.main()
