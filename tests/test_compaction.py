import json
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

    def test_safe_output_never_serializes_discarded_raw_text(self):
        marker = "RAW-DRAFT-MUST-NOT-LEAK"
        chunks = [ContextChunk(id="old", kind="draft", text=marker, metadata={"superseded": True})]
        result = compact("Fix auth", chunks, self.policy, self.mode, self.config["weights"])
        encoded = json.dumps(result.to_dict())
        self.assertNotIn(marker, encoded)
        self.assertNotIn("chunk", result.to_dict()["decisions"][0])

    def test_decision_and_essential_evidence_survive_low_lexical_relevance(self):
        chunks = [
            ContextChunk(id="decision", kind="decision", text="Retain the stable public API."),
            ContextChunk(id="proof", kind="evidence", text="Concurrency test reproduces duplicate writes.", metadata={"essential": True}),
        ]
        result = compact("Change colors", chunks, self.policy, self.mode, self.config["weights"])
        actions = {item.chunk.id: item.action for item in result.chunks}
        self.assertEqual(actions, {"decision": "keep", "proof": "keep"})

    def test_verified_exact_code_is_referenced_and_never_summarized(self):
        chunk = ContextChunk(
            id="code",
            kind="code",
            text="def verify():\n    return True",
            source="app/auth.py:10",
            metadata={"reopenable": True},
        )
        result = compact("verify auth", [chunk], self.policy, self.mode, self.config["weights"])
        self.assertEqual(result.chunks[0].action, "reference")
        self.assertNotIn("def verify", result.chunks[0].output_text or "")
        self.assertIn("app/auth.py:10", result.chunks[0].output_text or "")

    def test_unverified_exact_source_is_kept_verbatim(self):
        chunk = ContextChunk(id="code", kind="code", text="def verify():\n    return True", source="app/auth.py:10")
        result = compact("verify auth", [chunk], self.policy, self.mode, self.config["weights"])
        self.assertEqual(result.chunks[0].action, "keep")
        self.assertEqual(result.chunks[0].output_text, chunk.text)

    def test_protected_content_over_budget_is_explicitly_infeasible(self):
        policy = dict(self.policy)
        policy["context_budget_tokens"] = 10
        chunk = ContextChunk(id="constraint", kind="constraint", text="Never drop this requirement. " * 20)
        result = compact("Complete task", [chunk], policy, self.mode, self.config["weights"])
        self.assertEqual(result.status, "infeasible")
        self.assertGreater(result.estimated_tokens_after, result.budget_tokens)
        self.assertTrue(any("infeasible" in warning.lower() for warning in result.warnings))

    def test_model_estimator_is_recorded_with_safe_fallback(self):
        result = compact(
            "Fix auth",
            [ContextChunk(id="evidence", kind="evidence", text="The test fails.")],
            self.policy,
            self.mode,
            self.config["weights"],
            model="gpt-5",
        )
        self.assertEqual(result.model, "gpt-5")
        self.assertTrue(result.tokenizer.startswith(("tiktoken:", "chars/")))
        self.assertEqual(result.to_dict()["model"], "gpt-5")


if __name__ == "__main__":
    unittest.main()
