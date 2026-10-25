"""ui.read() against Bash's own `read`, on the same input."""
import io
import shutil
import subprocess
import unittest

from torquio import ui

INPUTS = [
    "1\n", "  12  \n", "\t7\t\n", "\n", "", "abc", "two words here\n", "first\nsecond\n",
    "a\\b\n", "a\\\\b\n", "trailing\\\n", "con\\\ntinued\n", "con\\\n", "\\ lead\n", "trail\\ \n",
    "café\n", "y\n", "  \n", "x\\\n\\\ny\n",
]

BASH = 'read {flags} v; s=$?; printf "%s|%s" "$v" "$s"'


@unittest.skipUnless(shutil.which("bash"), "needs bash")
class ReadMatchesBash(unittest.TestCase):
    def check(self, raw):
        for text in INPUTS:
            with self.subTest(input=text, raw=raw):
                p = subprocess.run(["bash", "-c", BASH.format(flags="-r" if raw else "")], input=text,
                                   capture_output=True, text=True)
                value, status = p.stdout.rsplit("|", 1)
                self.assertEqual(ui.read(raw=raw, stream=io.StringIO(text)), (value, status == "0"))

    def test_read(self):
        self.check(raw=False)

    def test_read_raw(self):
        self.check(raw=True)

    def test_prompt_only_on_a_terminal(self):
        # io.StringIO isn't a terminal, so nothing may be written (read -p behaves the same)
        stderr = io.StringIO()
        real, ui.sys.stderr = ui.sys.stderr, stderr
        try:
            ui.read("Select an option (1-7): ", stream=io.StringIO("3\n"))
        finally:
            ui.sys.stderr = real
        self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
