from __future__ import annotations

from collections import Counter
from .models import CompactResult


def compact_metrics(result: CompactResult) -> dict:
    actions = Counter(item.action for item in result.chunks)
    avoided = max(0, result.estimated_tokens_before - result.estimated_tokens_after)
    return {
        "mode": result.mode,
        "model": result.model,
        "tokenizer": result.tokenizer,
        "estimated_tokens_before": result.estimated_tokens_before,
        "estimated_tokens_after": result.estimated_tokens_after,
        "estimated_tokens_avoided": avoided,
        "estimated_savings_percent": round(result.savings_ratio * 100, 1),
        "status": result.status,
        "minimum_required_tokens": result.minimum_required_tokens,
        "actions": dict(actions),
        "warnings": result.warnings,
    }


def metric_line(result: CompactResult) -> str:
    metrics = compact_metrics(result)
    actions = metrics["actions"]
    return (
        f"Token Saver: ~{metrics['estimated_tokens_avoided']} input tokens avoided "
        f"({metrics['estimated_savings_percent']}%); "
        f"{actions.get('keep', 0)} kept, {actions.get('compress', 0)} compressed, "
        f"{actions.get('reference', 0)} referenced, {actions.get('discard', 0)} discarded; "
        f"mode={result.mode}; tokenizer={result.tokenizer}."
    )
