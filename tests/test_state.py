import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from token_saver.artifacts import ArtifactStore
from token_saver.state import HandoffStore, RunStore


class StateTests(unittest.TestCase):
    def test_run_store_is_append_only_and_summarizes_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RunStore(directory)
            first = store.record(
                "scope",
                "compact",
                {
                    "mode": "balanced",
                    "status": "ok",
                    "estimated_tokens_before": 100,
                    "estimated_tokens_after": 60,
                    "estimated_tokens_avoided": 40,
                    "estimated_savings_percent": 40.0,
                    "actions": {"keep": 1, "discard": 2},
                },
                tokenizer="chars/4",
            )
            second = store.record(
                "scope",
                "provider_usage",
                {"status": "reported"},
                provider_usage={"input_tokens": 50, "output_tokens": 10, "cost_usd": 0.01},
            )
            self.assertNotEqual(first["id"], second["id"])
            self.assertEqual(len(store.list("scope")), 2)
            self.assertEqual(store.summary("scope")["estimated_tokens_avoided"], 40)
            self.assertNotIn("total_tokens", store.summary("scope")["provider_usage_totals"])
            self.assertTrue(store.summary("scope")["provider_usage_available"])
            self.assertIn(first["id"], store.export_jsonl("scope"))

    def test_only_one_same_label_artifact_remains_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_file = root / "first.md"
            second_file = root / "second.md"
            first_file.write_text("first", encoding="utf-8")
            second_file.write_text("second", encoding="utf-8")
            store = ArtifactStore(root / "state", scope="shared")
            first = store.add(first_file, "plan")
            second = store.add(second_file, "plan")
            with ThreadPoolExecutor(max_workers=2) as pool:
                list(pool.map(store.accept, [first["id"], second["id"]]))
            accepted = store.list(accepted_only=True)
            self.assertEqual(len(accepted), 1)
            self.assertEqual({record["status"] for record in store.list()}, {"accepted", "superseded"})

    def test_handoff_replacement_is_valid_json_under_concurrency(self):
        with tempfile.TemporaryDirectory() as directory:
            store = HandoffStore(directory)
            with ThreadPoolExecutor(max_workers=6) as pool:
                list(pool.map(lambda index: store.save("shared", {"version": index}), range(20)))
            saved = store.show("shared")
            self.assertIsNotNone(saved)
            self.assertIn("version", saved["document"])
            json.dumps(saved)
            self.assertTrue(store.clear("shared"))
            self.assertIsNone(store.show("shared"))
