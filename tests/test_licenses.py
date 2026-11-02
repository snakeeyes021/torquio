"""License detection on made-up Wine prefixes."""
import json
import os
import tempfile
import unittest

from torquio import licenses

USER_DAT = "drive_c/users/me/AppData/Roaming/Steinberg/Activation Manager/Data/activation.dat"
CANTAI = "drive_c/users/me/AppData/Roaming/Cantai/Cantai.settings"


class Licenses(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.prefix = self.tmp.name

    def write(self, rel, text):
        path = os.path.join(self.prefix, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def activation(self, packages, bom=False):
        self.write(USER_DAT, ("﻿" if bom else "") + json.dumps({"ProductPackages": packages}))

    def test_no_prefix(self):
        self.assertEqual(licenses.steinberg_state(os.path.join(self.prefix, "missing")), "inactive")

    def test_no_activation_manager(self):
        os.makedirs(os.path.join(self.prefix, "drive_c"))
        self.assertEqual(licenses.steinberg_state(self.prefix), "inactive")

    def test_activation_manager_without_data(self):
        os.makedirs(os.path.join(self.prefix, "drive_c/Program Files/Steinberg/Activation Manager"))
        self.assertTrue(licenses.steinberg_state(self.prefix).startswith("unknown "))

    def test_active(self):
        self.activation([
            {"ProductPackage": "Dorico Pro 6", "LicensedItems": [{"jwt": "abc"}]},
            {"ProductPackage": "HALion Sonic", "LicensedItems": [{"jwt": ""}]},
            {"GrantID": "g-1", "LicensedItems": [{"jwt": "x"}, {}]},
        ], bom=True)
        self.assertEqual(licenses.steinberg_state(self.prefix), "active\nDorico Pro 6\ng-1")

    def test_deactivated(self):
        self.activation([{"ProductPackage": "Dorico Pro 6", "LicensedItems": [{"jwt": ""}]}])
        self.assertEqual(licenses.steinberg_state(self.prefix), "inactive")

    def test_unreadable(self):
        self.write(USER_DAT, "{oops")
        self.assertRegex(licenses.steinberg_state(self.prefix), r"^unknown couldn't read .* \(JSONDecodeError\)$")

    def test_cantai(self):
        self.assertEqual(licenses.active_plugins(self.prefix), [])
        self.write(CANTAI, '<VALUE name="activationToken" val=""/>')
        self.assertEqual(licenses.active_plugins(self.prefix), [])
        self.write(CANTAI, '<VALUE name="activationToken" val="tok"/>')
        plugins = licenses.active_plugins(self.prefix)
        self.assertEqual(plugins, [("Cantai", "in Cantai itself")])
        self.assertEqual(licenses.format_plugins(plugins), "Cantai\tin Cantai itself")


if __name__ == "__main__":
    unittest.main()
