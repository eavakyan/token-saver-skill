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


def request_report_text(report: dict) -> str:
    retrieval = report["retrieval"]
    skipped = (
        f"{retrieval['files_skipped_ignored']} ignored/"
        f"{retrieval['files_skipped_sensitive']} sensitive/"
        f"{retrieval['files_skipped_symlink']} symlink"
    )
    limit = "limit reached" if retrieval["limit_reached"] else "no scan limit reached"
    retrieval_line = (
        f"{retrieval['runs']} run(s); {retrieval['files_scanned']} files scanned; "
        f"{retrieval['passages_returned']} passages; skipped {skipped}; {limit}"
    )

    compaction = report["compaction"]
    if compaction["runs"]:
        compaction_line = (
            f"{compaction['estimated_tokens_before']} -> {compaction['estimated_tokens_after']} estimated tokens; "
            f"avoided {compaction['estimated_tokens_avoided']} "
            f"({compaction['estimated_savings_percent']}%)"
        )
    else:
        compaction_line = "no compaction run"

    statuses = report["statuses"]
    quality_line = ", ".join(
        f"{name} ({count})" for name, count in sorted(statuses.items())
    ) or "no recorded operations"
    if report.get("warnings"):
        quality_line += "; warnings: " + " | ".join(report["warnings"])

    if report["provider_usage_available"]:
        totals = report["provider_usage_totals"]
        provider_line = ", ".join(
            f"{name}={value}" for name, value in sorted(totals.items())
        ) or "reported"
    else:
        provider_line = "unavailable"

    return "\n".join((
        "Token Saver request report",
        f"- run: `{report['request_id']}`",
        f"- retrieval: {retrieval_line}",
        f"- compaction estimate: {compaction_line}",
        f"- quality/status: {quality_line}",
        f"- provider usage/cost: {provider_line}",
    ))
