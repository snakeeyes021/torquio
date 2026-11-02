"""`torquio api`: JSON only, and an error (exit code 2) for unknown verbs."""
import io
import json
import unittest
from unittest import mock

from torquio import api


class Api(unittest.TestCase):
    def test_unknown_verb(self):
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            self.assertEqual(api.main(["nope"]), 2)
        self.assertIn("version", json.loads(out.getvalue())["verbs"])

    def test_version(self):
        out = io.StringIO()
        with mock.patch.object(api.run, "capture", return_value=(0, "v0.7.0-alpha\n")), \
                mock.patch("sys.stdout", out):
            self.assertEqual(api.main(["version"]), 0)
        self.assertEqual(json.loads(out.getvalue())["torquio"], "v0.7.0-alpha")
        self.assertEqual(json.loads(out.getvalue())["api"], api.API_VERSION)


if __name__ == "__main__":
    unittest.main()
