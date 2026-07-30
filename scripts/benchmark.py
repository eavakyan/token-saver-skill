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
    corpus = json.loads((ROOT / "examples/benchmark_corpus.json").read_text(encoding="utf-8"))
    reports = []

    for case in corpus["cases"]:
        mode, policy = resolve_mode(config, case.get("mode"))
        chunks = [ContextChunk(**chunk) for chunk in case["chunks"]]
        result = compact(case["request"], chunks, policy, mode, config["weights"])
        report = {"name": case["name"], **compact_metrics(result)}
        reports.append(report)

    total_before = sum(r["estimated_tokens_before"] for r in reports)
    total_after = sum(r["estimated_tokens_after"] for r in reports)
    output = {
        "cases": reports,
        "aggregate": {
            "estimated_tokens_before": total_before,
            "estimated_tokens_after": total_after,
            "estimated_savings_percent": round((1 - total_after / max(1, total_before)) * 100, 1),
            "note": "Synthetic estimated context reduction; not a billing or quality guarantee.",
        },
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
