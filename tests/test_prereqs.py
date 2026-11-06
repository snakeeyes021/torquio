"""What's needed on the host, and how each kind of distribution installs it."""
import unittest

from torquio import prereqs

OS = {
    "fedora": 'NAME="Fedora Linux"\nID=fedora\nVERSION_ID=44\n',
    "silverblue": 'ID=fedora\nVARIANT_ID=silverblue\n',
    "bazzite": 'ID=bazzite\nID_LIKE="fedora"\n',
    "ubuntu": 'NAME="Ubuntu"\nID=ubuntu\nID_LIKE=debian\n',
    "mint": 'ID=linuxmint\nID_LIKE="ubuntu debian"\n',
    "pop": 'ID=pop\nID_LIKE="ubuntu debian"\n',
    "debian": 'ID=debian\n',
    "tumbleweed": 'ID="opensuse-tumbleweed"\nID_LIKE="opensuse suse"\n',
    "aeon": 'ID="opensuse-aeon"\nID_LIKE="opensuse suse"\n',
    "microos": 'ID="opensuse-microos"\nID_LIKE="opensuse suse"\n',
    "arch": 'ID=arch\n',
    "manjaro": 'ID=manjaro\nID_LIKE=arch\n',
    "endeavour": 'ID=endeavouros\nID_LIKE=arch\n',
    "steamos": 'ID=steamos\nID_LIKE=arch\n',
    "vanilla": 'ID=vanilla\n',
    "nixos": 'ID=nixos\n',
    "void": 'ID="void"\n',
    "rocky": 'ID="rocky"\nID_LIKE="rhel centos fedora"\n',
}


def fam(name, **kw):
    return prereqs.family(prereqs.parse_os_release(OS[name]), **kw)


class Families(unittest.TestCase):
    def test_families(self):
        expected = {"fedora": "dnf", "rocky": "dnf", "ubuntu": "apt", "mint": "apt", "pop": "apt",
                    "debian": "apt", "tumbleweed": "zypper", "aeon": "builtin", "microos": "image-suse", "arch": "pacman",
                    "manjaro": "pacman", "endeavour": "pacman", "steamos": "builtin", "vanilla": "builtin",
                    "nixos": "nix", "void": "unknown"}
        for name, family in expected.items():
            with self.subTest(name=name):
                self.assertEqual(fam(name), family)

    def test_image_based_fedora(self):
        self.assertEqual(fam("silverblue", ostree=True), "image-fedora")
        self.assertEqual(fam("bazzite", ostree=True), "builtin")  # Universal Blue: both included (README)
        self.assertEqual(fam("silverblue", ostree=True, ublue=True), "builtin")  # a downstream uBlue image
        self.assertEqual(fam("fedora", ostree=False), "dnf")


class Readme(unittest.TestCase):
    def test_the_readme_gives_the_same_commands(self):
        import os
        readme = open(os.path.join(os.path.dirname(__file__), "..", "README.md"), encoding="utf-8").read()
        for family, keys in (("dnf", ["distrobox"]), ("apt", ["distrobox", "podman"]),
                             ("pacman", ["distrobox", "podman"]), ("zypper", ["distrobox", "podman"])):
            with self.subTest(family=family):
                self.assertIn(prereqs.install_plan(family, keys)["shown"], readme)
        self.assertIn(prereqs.DISTROBOX_USER_INSTALL, readme)


class Plans(unittest.TestCase):
    def test_docker_stands_in_for_podman(self):
        self.assertEqual(prereqs.missing(True, False, False, True), ["distrobox"])
        self.assertEqual(prereqs.missing(True, True, False, False), ["podman"])
        self.assertEqual(prereqs.missing(False, True, True, False), ["python"])

    def test_commands(self):
        p = prereqs.install_plan("apt", ["distrobox", "podman"])
        # Shown as the README gives them; run without questions
        self.assertEqual(p["shown"], "sudo apt install distrobox podman")
        self.assertEqual(p["command"], "apt-get update && apt-get install -y distrobox podman")
        self.assertEqual(prereqs.install_plan("dnf", ["distrobox"])["shown"], "sudo dnf install distrobox")
        p = prereqs.install_plan("pacman", ["distrobox", "podman"])
        self.assertEqual(p["shown"], "sudo pacman -S distrobox podman")
        self.assertTrue(p["root"])
        self.assertEqual(prereqs.install_plan("apt", ["distrobox"])["alternative"], prereqs.DISTROBOX_USER_INSTALL)

    def test_image_based_systems_are_never_changed(self):
        for family in prereqs.IMAGE_FAMILIES:
            with self.subTest(family=family):
                p = prereqs.install_plan(family, ["distrobox"])
                self.assertEqual((p["command"], p["root"]), (prereqs.DISTROBOX_USER_INSTALL, False))
                p = prereqs.install_plan(family, ["distrobox", "podman"])
                self.assertEqual((p["command"], p["note"], p["note_keys"]),
                                 (prereqs.DISTROBOX_USER_INSTALL, "image", ["podman"]))
                for cmd in (p["command"], p["shown"]):
                    self.assertNotIn("rpm-ostree", cmd)
                    self.assertNotIn("transactional-update", cmd)

    def test_no_button_where_there_is_no_standard_command(self):
        for family, note in (("nix", "nix"), ("builtin", "builtin"), ("unknown", "unknown")):
            p = prereqs.install_plan(family, ["distrobox", "podman"])
            self.assertEqual((p["command"], p["note"], p["note_keys"]), ("", note, ["distrobox", "podman"]))
        self.assertIn("virtualisation.podman.enable = true;", prereqs.install_plan("nix", ["podman"])["config"])

    def test_nothing_missing(self):
        self.assertEqual(prereqs.install_plan("dnf", [])["command"], "")


if __name__ == "__main__":
    unittest.main()
