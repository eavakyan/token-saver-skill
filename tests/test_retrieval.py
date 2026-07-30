import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from token_saver.config import load_config, resolve_mode
from token_saver.retrieval import retrieve_with_stats


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        config = load_config()
        _, self.policy = resolve_mode(config, "balanced")

    def test_skips_external_symlink_sensitive_content_and_gitignored_files(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            (root / "safe.py").write_text("def refresh_token():\n    return 'safe'\n", encoding="utf-8")
            (root / "ignored.py").write_text("refresh_token ignored", encoding="utf-8")
            (root / "credentials.txt").write_text("api_key = 'abcdefghijklmnop'", encoding="utf-8")
            external = Path(outside) / "outside.py"
            external.write_text("refresh_token outside", encoding="utf-8")
            os.symlink(external, root / "linked.py")
            (root / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(root)], check=True)

            result = retrieve_with_stats(root, "refresh token", self.policy)
            paths = {passage.path for passage in result.passages}
            self.assertIn("safe.py", paths)
            self.assertNotIn("ignored.py", paths)
            self.assertNotIn("credentials.txt", paths)
            self.assertNotIn("linked.py", paths)
            self.assertTrue(result.stats.gitignore_applied)
            self.assertGreaterEqual(result.stats.files_skipped_sensitive, 1)
            self.assertGreaterEqual(result.stats.files_skipped_symlink, 1)

    def test_scan_limits_are_enforced_and_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index in range(10):
                (root / f"file-{index}.py").write_text("parser token\n", encoding="utf-8")
            policy = dict(self.policy)
            policy["max_files_scanned"] = 3
            result = retrieve_with_stats(root, "parser", policy)
            self.assertLessEqual(result.stats.files_considered, 3)
            self.assertTrue(result.stats.limit_reached)

    def test_invalid_limits_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                retrieve_with_stats(directory, "query", self.policy, top_files=0)
            with self.assertRaises(ValueError):
                retrieve_with_stats(directory, "query", self.policy, context_lines=-1)

    def test_context_lines_expand_a_known_hit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lines = ["before"] * 10 + ["unique_target"] + ["after"] * 10
            (root / "sample.py").write_text("\n".join(lines), encoding="utf-8")
            narrow = retrieve_with_stats(root, "unique target", self.policy, context_lines=1)
            wide = retrieve_with_stats(root, "unique target", self.policy, context_lines=6)
            self.assertGreater(len(wide.passages[0].text), len(narrow.passages[0].text))
