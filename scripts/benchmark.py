#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from token_saver.compaction import compact
from token_saver.config import load_config, resolve_mode
from token_saver.metrics import compact_metrics
from token_saver.models import ContextChunk


def main() -> int:
    config = load_config()
    corpus = json.loads((ROOT / "examples/evaluation_corpus.json").read_text(encoding="utf-8"))
    reports = []

    for case in corpus["cases"]:
        mode, policy = resolve_mode(config, case.get("mode"))
        policy.update(case.get("policy_overrides", {}))
        chunks = [ContextChunk(**chunk) for chunk in case["chunks"]]
        result = compact(case["request"], chunks, policy, mode, config["weights"])
        actions = {item.chunk.id: item.action for item in result.chunks}
        safe_output = json.dumps(result.to_dict(), ensure_ascii=False)
        failures = []
        for chunk_id in case.get("must_preserve_ids", []):
            if actions.get(chunk_id) == "discard" or chunk_id not in actions:
                failures.append(f"required chunk {chunk_id!r} was not preserved")
        for chunk_id in case.get("must_discard_ids", []):
            if actions.get(chunk_id) != "discard":
                failures.append(f"low-value chunk {chunk_id!r} was not discarded")
        for marker in case.get("raw_text_must_not_appear", []):
            if marker in safe_output:
                failures.append(f"raw marker {marker!r} leaked into handoff output")
        expected_status = case.get("expected_status", "ok")
        if result.status != expected_status:
            failures.append(f"expected status {expected_status!r}; found {result.status!r}")
        report = {
            "name": case["name"],
            **compact_metrics(result),
            "quality_pass": not failures,
            "quality_failures": failures,
        }
        reports.append(report)

    total_before = sum(r["estimated_tokens_before"] for r in reports)
    total_after = sum(r["estimated_tokens_after"] for r in reports)
    output = {
        "cases": reports,
        "aggregate": {
            "estimated_tokens_before": total_before,
            "estimated_tokens_after": total_after,
            "estimated_savings_percent": round((1 - total_after / max(1, total_before)) * 100, 1),
            "quality_pass": all(report["quality_pass"] for report in reports),
            "note": "Representative regression fixtures using approximate token estimates; not a billing guarantee.",
        },
    }
    print(json.dumps(output, indent=2))
    return 0 if output["aggregate"]["quality_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
