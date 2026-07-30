from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from .text import lexical_relevance, terms


@dataclass(slots=True)
class Passage:
    path: str
    start_line: int
    end_line: int
    score: float
    text: str

    def to_dict(self):
        return asdict(self)


def _is_probably_text(path: Path) -> bool:
    try:
        sample = path.read_bytes()[:4096]
    except OSError:
        return False
    return b"\x00" not in sample


def iter_candidate_files(root: Path, config: dict) -> Iterable[Path]:
    excluded_dirs = set(config["exclude_dirs"])
    excluded_files = set(config["exclude_files"])
    allowed = set(config["allowed_extensions"])
    max_bytes = int(config["max_file_bytes"])

    for current, dirs, names in os.walk(root):
        dirs[:] = [name for name in dirs if name not in excluded_dirs]
        current_path = Path(current)
        for name in names:
            path = current_path / name
            if name in excluded_files or path.suffix.lower() not in allowed:
                continue
            try:
                if path.stat().st_size > max_bytes:
                    continue
            except OSError:
                continue
            if _is_probably_text(path):
                yield path


def _line_scores(query: str, lines: list[str]) -> list[tuple[float, int]]:
    q_terms = set(terms(query))
    scores = []
    for i, line in enumerate(lines):
        line_terms = set(terms(line))
        overlap = len(q_terms & line_terms) / max(1, len(q_terms))
        scores.append((overlap, i))
    return scores


def retrieve(
    root: str | Path,
    query: str,
    config: dict,
    top_files: int | None = None,
    passages_per_file: int | None = None,
) -> list[Passage]:
    root_path = Path(root).resolve()
    ranked_files: list[tuple[float, Path, str]] = []

    for path in iter_candidate_files(root_path, config):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel_path = str(path.relative_to(root_path))
        preview = text[:20000]
        score = 0.35 * lexical_relevance(query, rel_path) + 0.65 * lexical_relevance(query, preview)
        if score > 0:
            ranked_files.append((score, path, text))

    ranked_files.sort(key=lambda item: item[0], reverse=True)
    file_limit = top_files or int(config["top_files"])
    passage_limit = passages_per_file or int(config["passages_per_file"])
    context_lines = int(config["passage_context_lines"])
    max_chars = int(config["max_passage_chars"])
    results: list[Passage] = []

    for file_score, path, text in ranked_files[:file_limit]:
        lines = text.splitlines()
        ranked_lines = sorted(_line_scores(query, lines), reverse=True)
        selected: list[tuple[int, int]] = []

        for line_score, index in ranked_lines:
            if line_score <= 0 and selected:
                break
            start = max(0, index - context_lines)
            end = min(len(lines), index + context_lines + 1)
            if any(not (end <= a or start >= b) for a, b in selected):
                continue
            selected.append((start, end))
            if len(selected) >= passage_limit:
                break

        if not selected and lines:
            selected = [(0, min(len(lines), context_lines * 2 + 1))]

        for start, end in sorted(selected):
            passage_text = "\n".join(lines[start:end])
            if len(passage_text) > max_chars:
                passage_text = passage_text[:max_chars] + "\n[…truncated]"
            local_score = lexical_relevance(query, passage_text)
            results.append(Passage(
                path=str(path.relative_to(root_path)),
                start_line=start + 1,
                end_line=end,
                score=round(0.5 * file_score + 0.5 * local_score, 4),
                text=passage_text,
            ))

    results.sort(key=lambda passage: passage.score, reverse=True)
    return results
