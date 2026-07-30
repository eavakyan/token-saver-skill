from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .text import fingerprint

ChunkKind = Literal[
    "accepted_artifact", "constraint", "current_request", "decision", "evidence",
    "exact", "code", "source_passage", "tool_result", "summary", "draft", "critique",
    "rejected_source", "reasoning", "unknown"
]

Action = Literal["keep", "compress", "reference", "discard"]


@dataclass(slots=True)
class ContextChunk:
    id: str
    text: str
    kind: ChunkKind = "unknown"
    source: str | None = None
    created_at: str | None = None
    accepted: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ScoredChunk:
    chunk: ContextChunk
    score: float
    action: Action
    estimated_tokens_before: int
    estimated_tokens_after: int
    reason: str
    output_text: str | None = None

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.chunk.text)[:12]

    def decision_dict(self) -> dict[str, Any]:
        """Serialize a decision without ever echoing the original input text."""
        return {
            "id": self.chunk.id,
            "kind": self.chunk.kind,
            "source": self.chunk.source,
            "fingerprint": self.fingerprint,
            "score": self.score,
            "action": self.action,
            "estimated_tokens_before": self.estimated_tokens_before,
            "estimated_tokens_after": self.estimated_tokens_after,
            "reason": self.reason,
        }

    def handoff_dict(self) -> dict[str, Any]:
        return {
            "id": self.chunk.id,
            "kind": self.chunk.kind,
            "source": self.chunk.source,
            "fingerprint": self.fingerprint,
            "content": self.output_text,
        }


@dataclass(slots=True)
class CompactResult:
    request: str
    mode: str
    budget_tokens: int
    estimated_tokens_before: int
    estimated_tokens_after: int
    minimum_required_tokens: int
    chunks: list[ScoredChunk]
    status: Literal["ok", "infeasible"] = "ok"
    warnings: list[str] = field(default_factory=list)

    @property
    def savings_ratio(self) -> float:
        if self.estimated_tokens_before <= 0:
            return 0.0
        return max(0.0, 1.0 - self.estimated_tokens_after / self.estimated_tokens_before)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request,
            "mode": self.mode,
            "budget_tokens": self.budget_tokens,
            "estimated_tokens_before": self.estimated_tokens_before,
            "estimated_tokens_after": self.estimated_tokens_after,
            "minimum_required_tokens": self.minimum_required_tokens,
            "estimated_savings_ratio": round(self.savings_ratio, 4),
            "status": self.status,
            "warnings": self.warnings,
            "context": [chunk.handoff_dict() for chunk in self.chunks if chunk.output_text is not None],
            "decisions": [chunk.decision_dict() for chunk in self.chunks],
        }
