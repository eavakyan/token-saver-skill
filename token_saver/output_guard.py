from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    errors: list[str]
    measurements: dict[str, Any]

    def to_dict(self):
        return asdict(self)


WORD_RE = re.compile(r"\b[\w’'-]+\b", re.UNICODE)
BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+", re.MULTILINE)


def validate_output(
    text: str,
    exact_words: int | None = None,
    max_words: int | None = None,
    exact_bullets: int | None = None,
    require_json: bool = False,
    required_headings: list[str] | None = None,
) -> ValidationResult:
    errors: list[str] = []
    words = WORD_RE.findall(text)
    bullets = BULLET_RE.findall(text)
    parsed_json = None

    if exact_words is not None and len(words) != exact_words:
        errors.append(f"Expected exactly {exact_words} words; found {len(words)}.")
    if max_words is not None and len(words) > max_words:
        errors.append(f"Expected at most {max_words} words; found {len(words)}.")
    if exact_bullets is not None and len(bullets) != exact_bullets:
        errors.append(f"Expected exactly {exact_bullets} bullets; found {len(bullets)}.")
    if require_json:
        try:
            parsed_json = json.loads(text)
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}.")
    for heading in required_headings or []:
        if heading not in text:
            errors.append(f"Missing required heading: {heading}")

    return ValidationResult(
        valid=not errors,
        errors=errors,
        measurements={
            "words": len(words),
            "bullets": len(bullets),
            "json_type": type(parsed_json).__name__ if parsed_json is not None else None,
        },
    )
