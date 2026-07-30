import unittest

from token_saver.compaction import compact
from token_saver.config import load_config, resolve_mode
from token_saver.models import ContextChunk


class CompactionTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()
        self.mode, self.policy = resolve_mode(self.config, "balanced")

    def test_hard_keep_survives(self):
        chunks = [
            ContextChunk(id="c", kind="constraint", text="Do not change the public API."),
            ContextChunk(id="d", kind="draft", text="irrelevant abandoned draft " * 200, metadata={"superseded": True}),
        ]
        result = compact("Fix auth", chunks, self.policy, self.mode, self.config["weights"])
        actions = {item.chunk.id: item.action for item in result.chunks}
        self.assertEqual(actions["c"], "keep")
        self.assertEqual(actions["d"], "discard")

    def test_duplicate_removed(self):
        chunks = [
            ContextChunk(id="a", kind="evidence", text="Same evidence about parser failure."),
            ContextChunk(id="b", kind="evidence", text="Same evidence about parser failure."),
        ]
        result = compact("parser failure", chunks, self.policy, self.mode, self.config["weights"])
        self.assertEqual(sum(item.action == "discard" for item in result.chunks), 1)


if __name__ == "__main__":
    unittest.main()
