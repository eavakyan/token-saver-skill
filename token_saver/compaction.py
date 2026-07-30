from __future__ import annotations

import re
from collections import defaultdict

from .models import CompactResult, ContextChunk, ScoredChunk
from .text import compact_whitespace, fingerprint, lexical_relevance, terms
from .tokenizer import estimate_tokens

HARD_KEEP = {"accepted_artifact", "constraint", "current_request"}
REFERENCEABLE = {"source_passage", "evidence", "tool_result"}
LOW_VALUE = {"draft", "critique", "rejected_source", "reasoning"}

SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def _uniqueness(text: str, seen: set[str]) -> float:
    fp = fingerprint(text)
    if fp in seen:
        return 0.0
    seen.add(fp)
    return 1.0


def _freshness(chunk: ContextChunk) -> float:
    if chunk.metadata.get("superseded") or chunk.metadata.get("rejected"):
        return 0.05
    if chunk.accepted or chunk.kind == "accepted_artifact":
        return 1.0
    return float(chunk.metadata.get("freshness", 0.85))


def _authority(chunk: ContextChunk) -> float:
    if chunk.kind in {"constraint", "current_request", "accepted_artifact", "decision"}:
        return 1.0
    if chunk.kind in {"evidence", "source_passage"}:
        return float(chunk.metadata.get("authority", 0.95))
    if chunk.metadata.get("primary_source") or chunk.metadata.get("verified"):
        return 0.95
    return float(chunk.metadata.get("authority", 0.8))


def _dependency(chunk: ContextChunk) -> float:
    if chunk.kind in HARD_KEEP or chunk.metadata.get("required"):
        return 1.0
    if chunk.kind in {"evidence", "source_passage"}:
        return float(chunk.metadata.get("dependency", 0.95))
    return float(chunk.metadata.get("dependency", 0.8))


def _summarize(text: str, query: str, target_chars: int) -> str:
    clean = compact_whitespace(text)
    if len(clean) <= target_chars:
        return clean

    sentences = [s.strip() for s in SENTENCE_RE.split(clean) if s.strip()]
    if not sentences:
        return clean[:target_chars]

    q_terms = set(terms(query))
    scored = []
    for index, sentence in enumerate(sentences):
        s_terms = set(terms(sentence))
        relevance = len(q_terms & s_terms) / max(1, len(q_terms))
        signal = 0.0
        if re.search(r"\b(must|shall|error|failed|decision|because|risk|test|result|path|line|version)\b", sentence, re.I):
            signal += 0.25
        if re.search(r"\b\d+(?:\.\d+)?\b", sentence):
            signal += 0.10
        position = max(0.0, 0.12 - index * 0.005)
        scored.append((relevance + signal + position, index, sentence))

    chosen = []
    used = 0
    for _, index, sentence in sorted(scored, reverse=True):
        if used + len(sentence) + 1 > target_chars and chosen:
            continue
        chosen.append((index, sentence))
        used += len(sentence) + 1
        if used >= target_chars * 0.85:
            break

    chosen.sort()
    summary = " ".join(sentence for _, sentence in chosen)
    return summary[:target_chars].rstrip()


def compact(
    request: str,
    chunks: list[ContextChunk],
    config: dict,
    mode_name: str,
    weights: dict[str, float],
) -> CompactResult:
    chars_per_token = float(config["chars_per_token"])
    budget = int(config["context_budget_tokens"])
    threshold = float(config["min_chunk_score"])
    summary_ratio = float(config["summary_ratio"])
    seen: set[str] = set()
    scored: list[ScoredChunk] = []

    request_tokens = estimate_tokens(request, chars_per_token)
    before = request_tokens + sum(estimate_tokens(chunk.text, chars_per_token) for chunk in chunks)

    for chunk in chunks:
        token_before = estimate_tokens(chunk.text, chars_per_token)
        uniqueness = _uniqueness(chunk.text, seen)
        relevance = 1.0 if chunk.kind in HARD_KEEP else lexical_relevance(request, chunk.text)
        weight = float(weights.get(chunk.kind, weights.get("unknown", 0.45)))
        score = weight * relevance * _freshness(chunk) * _authority(chunk) * uniqueness * _dependency(chunk)

        if chunk.kind in HARD_KEEP or chunk.metadata.get("required"):
            action = "keep"
            reason = "hard-preserved task contract or accepted work"
        elif uniqueness == 0.0:
            action = "discard"
            reason = "exact duplicate"
        elif chunk.metadata.get("superseded") or chunk.metadata.get("rejected"):
            action = "discard"
            reason = "superseded or rejected"
        elif score < threshold:
            action = "discard"
            reason = f"ROI score {score:.3f} below {threshold:.3f}"
        elif token_before > max(120, budget // 18):
            action = "compress"
            reason = "relevant but verbose"
        elif chunk.kind in REFERENCEABLE and chunk.source and token_before > 180:
            action = "reference"
            reason = "source can be reopened cheaply"
        else:
            action = "keep"
            reason = "compact and relevant"

        output_text: str | None
        if action == "keep":
            output_text = compact_whitespace(chunk.text)
        elif action == "compress":
            target = max(240, int(len(chunk.text) * summary_ratio))
            output_text = _summarize(chunk.text, request, target)
        elif action == "reference":
            output_text = f"[Reference: {chunk.source}; id={chunk.id}; fingerprint={fingerprint(chunk.text)[:12]}]"
        else:
            output_text = None

        token_after = estimate_tokens(output_text or "", chars_per_token)
        scored.append(ScoredChunk(
            chunk=chunk,
            score=round(score, 4),
            action=action,
            estimated_tokens_before=token_before,
            estimated_tokens_after=token_after,
            reason=reason,
            output_text=output_text,
        ))

    # Enforce budget by demoting the lowest-value non-hard-kept chunks.
    current = request_tokens + sum(item.estimated_tokens_after for item in scored)
    if current > budget:
        candidates = sorted(
            (item for item in scored if item.chunk.kind not in HARD_KEEP and item.action != "discard"),
            key=lambda item: item.score,
        )
        for item in candidates:
            if current <= budget:
                break
            old = item.estimated_tokens_after
            if item.chunk.source and item.action == "keep":
                item.action = "reference"
                item.output_text = f"[Reference: {item.chunk.source}; id={item.chunk.id}]"
                item.reason += "; demoted to meet budget"
            else:
                item.action = "discard"
                item.output_text = None
                item.reason += "; discarded to meet budget"
            item.estimated_tokens_after = estimate_tokens(item.output_text or "", chars_per_token)
            current -= old - item.estimated_tokens_after

    warnings = []
    ratio = current / max(1, budget)
    if ratio >= float(config["fresh_task_ratio"]):
        warnings.append("Fresh-task threshold reached: continue with only the task contract, accepted artifact, decisions, open issues, and essential evidence.")
    elif ratio >= float(config["compact_ratio"]):
        warnings.append("Compaction threshold reached: avoid adding context unless it changes the decision.")
    elif ratio >= float(config["warn_ratio"]):
        warnings.append("Warning threshold reached: retrieve narrowly and avoid speculative context.")

    return CompactResult(
        request=request,
        mode=mode_name,
        budget_tokens=budget,
        estimated_tokens_before=before,
        estimated_tokens_after=current,
        chunks=scored,
        warnings=warnings,
    )
