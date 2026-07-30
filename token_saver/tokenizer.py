from __future__ import annotations

import math
from functools import lru_cache


@lru_cache(maxsize=4)
def _get_encoder(model: str):
    try:
        import tiktoken  # type: ignore
    except ImportError:
        return None
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def estimate_tokens(text: str, chars_per_token: float = 4.0, model: str | None = None) -> int:
    if not text:
        return 0
    if model:
        encoder = _get_encoder(model)
        if encoder is not None:
            return len(encoder.encode(text))
    return max(1, math.ceil(len(text) / max(chars_per_token, 1.0)))


def tokenizer_label(chars_per_token: float = 4.0, model: str | None = None) -> str:
    """Return the estimator used, without claiming provider billing accuracy."""
    if model and _get_encoder(model) is not None:
        return f"tiktoken:{model}"
    return f"chars/{max(chars_per_token, 1.0):g}"
