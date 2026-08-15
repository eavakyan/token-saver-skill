import tempfile
import unittest
from pathlib import Path

from token_saver.config import load_config, resolve_mode


class ConfigTests(unittest.TestCase):
    def test_packaged_default_loads(self):
        self.assertEqual(load_config()["default_mode"], "balanced")

    def test_retrieval_defaults_stage_evidence_by_mode(self):
        config = load_config()
        expected = {
            "quality-first": (14, 5),
            "balanced": (6, 2),
            "extreme": (4, 2),
        }
        for mode, limits in expected.items():
            _, policy = resolve_mode(config, mode)
            self.assertEqual((policy["top_files"], policy["passages_per_file"]), limits)

    def test_missing_override_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                load_config(Path(directory) / "missing.toml")
