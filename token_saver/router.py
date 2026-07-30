from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class RouteRecommendation:
    tier: str
    model: str
    reasoning_effort: str
    score: int
    reasons: list[str]
    advisory: bool = True


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
    risk_terms = any(term in text for term in (
        "production", "security", "credential", "permission", "legal", "medical",
        "financial", "data loss", "destructive", "incident", "outage",
    ))

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
    if high_stakes or risk_terms:
        score += 1; reasons.append("high cost of failure")
    complex_shape = ambiguous or architecture or debug_unclear or cross_domain or adversarial or file_count > 5
    if deterministic and not (high_stakes or risk_terms or complex_shape):
        score -= 2; reasons.append("bounded deterministic transformation")
    elif simple:
        score -= 1; reasons.append("simple extraction or transformation")

    difficult = architecture or adversarial or debug_unclear or (ambiguous and file_count > 5) or (cross_domain and file_count > 5)
    if high_stakes or risk_terms or difficult or score >= 4:
        tier, model, effort = "powerful", "gpt-5.6-sol", "high"
    elif deterministic and not complex_shape:
        tier, model, effort = "economy", "platform-economy-model", "low"
    else:
        tier, model, effort = "standard", "gpt-5.6-terra", "medium"
    return RouteRecommendation(
        tier=tier,
        model=model,
        reasoning_effort=effort,
        score=score,
        reasons=reasons or ["routine task complexity"],
    )
