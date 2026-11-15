"""The machine ID (which plug-in licenses like Cantai's are tied to, with limited activations) is never changed
from an automatic path, and with Cantai installed only after a typed confirmation."""
import unittest
from unittest import mock

from torquio.cli import engine as engine_cli

A, B = "a" * 32, "b" * 32


class IdentityGuard(unittest.TestCase):
    def setUp(self):
        for p in (mock.patch.object(engine_cli.identity, "derived_machine_id", return_value=A),
                  mock.patch.object(engine_cli.identity, "container_machine_id", return_value=B),
                  mock.patch.object(engine_cli.licenses, "active_plugins", return_value=[])):
            p.start()
            self.addCleanup(p.stop)
        self.enter = mock.patch.object(engine_cli, "_enter", return_value=0).start()
        self.addCleanup(mock.patch.stopall)

    def test_automatic_path_never_changes_it(self):
        with mock.patch.object(engine_cli.ui, "ask", side_effect=AssertionError("asked")):
            self.assertEqual(engine_cli.fix_machine_identity(quiet=True), 0)
        self.enter.assert_not_called()

    def test_with_cantai_installed_yes_is_not_enough(self):
        with mock.patch("torquio.plugins.cantai_installed", return_value=True), \
                mock.patch.object(engine_cli.ui, "ask", return_value="y"):
            self.assertEqual(engine_cli.fix_machine_identity(), 0)
        self.enter.assert_not_called()

    def test_with_cantai_installed_the_typed_confirmation_goes_ahead(self):
        with mock.patch("torquio.plugins.cantai_installed", return_value=True), \
                mock.patch.object(engine_cli.ui, "ask", return_value="Cantai is deactivated"):
            engine_cli.fix_machine_identity(strict=False)
        self.enter.assert_called_once()

    def test_active_plugins_refuse(self):
        engine_cli.licenses.active_plugins.return_value = [("Cantai", "in Cantai itself")]
        with mock.patch.object(engine_cli.ui, "ask", side_effect=AssertionError("asked")):
            self.assertEqual(engine_cli.fix_machine_identity(), 0)
        self.enter.assert_not_called()


if __name__ == "__main__":
    unittest.main()
