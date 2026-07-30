from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal

ChunkKind = Literal[
    "accepted_artifact", "constraint", "current_request", "decision", "evidence",
    "source_passage", "tool_result", "summary", "draft", "critique",
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

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        return result


@dataclass(slots=True)
class CompactResult:
    request: str
    mode: str
    budget_tokens: int
    estimated_tokens_before: int
    estimated_tokens_after: int
    chunks: list[ScoredChunk]
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
            "estimated_savings_ratio": round(self.savings_ratio, 4),
            "warnings": self.warnings,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
        }
