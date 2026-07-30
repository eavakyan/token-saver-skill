from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class RouteRecommendation:
    tier: str
    score: int
    reasons: list[str]


def recommend_tier(request: str, file_count: int = 0, high_stakes: bool = False) -> RouteRecommendation:
    text = request.lower()
    score = 0
    reasons: list[str] = []

    deterministic = any(term in text for term in (
        "format", "convert", "extract", "rename", "sort", "count", "exactly",
        "valid json", "replace", "lint", "prettify"
    ))
    simple = any(term in text for term in ("summarize this", "translate", "list the", "find occurrences"))
    ambiguous = any(term in text for term in ("explore", "figure out", "best approach", "investigate", "unknown"))
    architecture = any(term in text for term in ("architecture", "migration", "redesign", "system design", "strategy"))
    debug_unclear = ("debug" in text or "fix" in text) and not any(
        term in text for term in ("failing test", "stack trace", "reproduce", "error:")
    )
    cross_domain = len(set(re.findall(r"\b(api|database|frontend|backend|security|infra|legal|finance|medical)\b", text))) >= 2
    adversarial = any(term in text for term in ("threat model", "adversarial", "formal verification", "deep review"))

    if file_count > 5:
        score += 1; reasons.append("more than five relevant files")
    if ambiguous:
        score += 1; reasons.append("ambiguous or exploratory requirements")
    if architecture:
        score += 1; reasons.append("architecture or migration design")
    if debug_unclear:
        score += 1; reasons.append("debugging without a clear reproduction")
    if cross_domain:
        score += 1; reasons.append("cross-domain synthesis")
    if adversarial:
        score += 1; reasons.append("adversarial or formal review")
    if high_stakes or any(term in text for term in ("production outage", "security critical", "legal advice", "medical", "financial filing")):
        score += 1; reasons.append("high cost of failure")
    if deterministic:
        score -= 2; reasons.append("bounded deterministic transformation")
    elif simple:
        score -= 1; reasons.append("simple extraction or transformation")

    tier = "economy" if score <= 0 else "standard" if score <= 3 else "powerful"
    return RouteRecommendation(tier=tier, score=score, reasons=reasons or ["normal task complexity"])
