from __future__ import annotations

import hashlib
import re
from collections import Counter

WORD_RE = re.compile(r"[A-Za-z0-9_./:@+-]+")
SPACE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    return SPACE_RE.sub(" ", text).strip().lower()


def fingerprint(text: str) -> str:
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def terms(text: str) -> list[str]:
    return [token.lower() for token in WORD_RE.findall(text) if len(token) > 2]


def term_counts(text: str) -> Counter[str]:
    return Counter(terms(text))


def lexical_relevance(query: str, text: str) -> float:
    q = set(terms(query))
    if not q:
        return 0.5
    t = set(terms(text))
    overlap = len(q & t) / len(q)
    phrase_bonus = 0.15 if normalize(query) in normalize(text) else 0.0
    return min(1.0, overlap + phrase_bonus)


def compact_whitespace(text: str) -> str:
    lines = [SPACE_RE.sub(" ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)
