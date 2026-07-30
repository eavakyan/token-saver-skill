import tempfile
import unittest
from pathlib import Path

from token_saver.config import load_config


class ConfigTests(unittest.TestCase):
    def test_packaged_default_loads(self):
        self.assertEqual(load_config()["default_mode"], "balanced")

    def test_missing_override_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                load_config(Path(directory) / "missing.toml")
