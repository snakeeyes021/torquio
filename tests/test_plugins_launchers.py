"""What installed plug-ins need (Cantai: WebView2 and vkd3d-proton), stale launchers, and finding Cantai's download
however it was saved (zip, unzipped folder, setup program)."""
import os
import tempfile
import unittest
from unittest import mock

from torquio import paths, plugins
from torquio.cli import install, update

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def touch(path, text=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = self.tmp.name
        self.prefix = os.path.join(self.home, ".local/share/torquio/prefix")
        self.data = os.path.join(self.home, ".local/share/torquio")
        os.makedirs(self.prefix)
        for p in (mock.patch.object(paths, "home", return_value=self.home),
                  mock.patch.object(paths, "prefix_dir", return_value=self.prefix),
                  mock.patch.object(paths, "data_dir", return_value=self.data),
                  mock.patch.object(paths, "repo_dir", return_value=REPO)):
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        self.tmp.cleanup()


class Plugins(Base):
    def cantai(self):
        touch(os.path.join(self.prefix, "drive_c/users/me/AppData/Local/Programs/Common/VST3/Cantai.vst3/x"))

    def webview2(self, env=True):
        touch(os.path.join(self.prefix, "drive_c/Program Files/Torquio/WebView2/140.0/msedgewebview2.exe"))
        touch(os.path.join(self.prefix, "user.reg"),
              '[Environment]\n"WEBVIEW2_BROWSER_EXECUTABLE_FOLDER"="C:\\\\x"\n' if env else "[Environment]\n")

    def vkd3d(self):
        version = open(os.path.join(REPO, plugins.SCRIPTS["vkd3d-proton"])).read().split('VKD3D_PROTON_VERSION="')[1].split('"')[0]
        for dll in ("d3d12.dll", "d3d12core.dll"):
            touch(os.path.join(self.data, "vkd3d-proton", version, dll))

    def test_nothing_without_cantai(self):
        self.assertEqual(plugins.missing(), [])

    def test_cantai_installed_another_way_needs_both(self):
        self.cantai()
        self.assertEqual(plugins.missing(), ["webview2", "vkd3d-proton"])

    def test_runtime_without_the_prefix_pointing_at_it_still_missing(self):
        self.cantai()
        self.webview2(env=False)
        self.vkd3d()
        self.assertEqual(plugins.missing(), ["webview2"])

    def test_all_there(self):
        self.cantai()
        self.webview2()
        self.vkd3d()
        self.assertEqual(plugins.missing(), [])

    def test_provision_runs_only_whats_missing(self):
        self.cantai()
        self.vkd3d()
        with mock.patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}), \
                mock.patch.object(plugins.run, "interactive", return_value=0) as ran:
            self.assertEqual(plugins.provision(), 0)
        self.assertEqual([os.path.basename(c.args[0][0]) for c in ran.call_args_list], ["install_webview2.sh"])

    def test_webview2_waits_for_the_desktop(self):
        self.cantai()
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch.object(plugins.run, "interactive", return_value=0) as ran:
            self.assertEqual(plugins.provision(), 0)
        self.assertEqual([os.path.basename(c.args[0][0]) for c in ran.call_args_list], ["install_vkd3d_proton.sh"])


class Launchers(Base):
    def setUp(self):
        super().setUp()
        touch(os.path.join(self.prefix, ".torquio_core_installed"))
        self.bindir = os.path.join(self.home, ".local/bin")

    def test_missing_launchers_are_written_once_installed(self):
        self.assertEqual(update.ensure_launchers(), list(update.LAUNCHERS))
        self.assertEqual(update.stale_launchers(), [])

    def test_old_bash_launcher_is_replaced(self):
        update.install_launchers()
        touch(os.path.join(self.bindir, "torquio-dorico"), "#!/bin/bash\n# July\n")
        self.assertEqual(update.ensure_launchers(), ["torquio-dorico"])
        self.assertIn(f'REPO = "{REPO}"', open(os.path.join(self.bindir, "torquio-dorico")).read())

    def test_another_existing_copys_launchers_are_left_alone(self):
        other = os.path.join(self.home, "other-torquio")
        touch(os.path.join(other, "torquio"))
        update.install_launchers()
        text = open(os.path.join(self.bindir, "torquio-sam")).read().replace(REPO, other)
        touch(os.path.join(self.bindir, "torquio-sam"), text)
        self.assertEqual(update.stale_launchers(), [])

    def test_rewriting_one_leaves_another_copys_and_the_command_alone(self):
        other = os.path.join(self.home, "other-torquio")
        touch(os.path.join(other, "torquio"))
        update.install_launchers()
        for name in ("torquio-sam", "torquio-sda-handler"):
            path = os.path.join(self.bindir, name)
            with open(path) as f:
                text = f.read().replace(REPO, other)
            touch(path, text)
        os.remove(os.path.join(self.bindir, "torquio"))
        os.symlink(os.path.join(other, "torquio"), os.path.join(self.bindir, "torquio"))
        touch(os.path.join(self.bindir, "torquio-dorico"), "#!/bin/bash\n# July\n")
        self.assertEqual(update.ensure_launchers(), ["torquio-dorico"])
        with open(os.path.join(self.bindir, "torquio-sam")) as f:
            self.assertIn(f'REPO = "{other}"', f.read())
        self.assertEqual(os.readlink(os.path.join(self.bindir, "torquio")), os.path.join(other, "torquio"))

    def test_launchers_of_a_copy_that_is_gone_are_replaced(self):
        update.install_launchers()
        text = open(os.path.join(self.bindir, "torquio-sam")).read().replace(REPO, "/nowhere/torquio")
        touch(os.path.join(self.bindir, "torquio-sam"), text)
        self.assertEqual(update.stale_launchers(), ["torquio-sam"])

    def test_nothing_before_torquio_is_installed(self):
        os.remove(os.path.join(self.prefix, ".torquio_core_installed"))
        self.assertEqual(update.ensure_launchers(), [])
        self.assertFalse(os.path.exists(os.path.join(self.bindir, "torquio-dorico")))


class CantaiDownload(unittest.TestCase):
    def find(self, *names, folders=()):
        with tempfile.TemporaryDirectory() as d:
            for n in names:
                touch(os.path.join(d, n))
            for n in folders:
                touch(os.path.join(d, n, "CantaiLocalRenderVST-4.0.2-Setup.exe"))
            found = install.find_installer(install.INSTALLER_PATTERNS["cantai"], [d])
            return os.path.basename(found)

    def test_zip(self):
        self.assertEqual(self.find("Cantai-Windows-Installer-v4.0.2.exe.zip"), "Cantai-Windows-Installer-v4.0.2.exe.zip")

    def test_unzipped_folder(self):
        self.assertEqual(self.find(folders=["Cantai-Windows-Installer-v4.0.2.exe"]), "Cantai-Windows-Installer-v4.0.2.exe")

    def test_setup_program(self):
        self.assertEqual(self.find("CantaiLocalRenderVST-4.0.2-Setup.exe"), "CantaiLocalRenderVST-4.0.2-Setup.exe")

    def test_other_installers_still_single_pattern(self):
        with tempfile.TemporaryDirectory() as d:
            touch(os.path.join(d, "NotePerformer-Installer-5.1.2.exe"))
            self.assertTrue(install.find_installer(install.INSTALLER_PATTERNS["noteperformer"], [d]))


if __name__ == "__main__":
    unittest.main()
