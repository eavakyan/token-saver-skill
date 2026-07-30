from __future__ import annotations

import fnmatch
import heapq
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from .text import lexical_relevance, terms


SENSITIVE_CONTENT = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(?i:(?:aws_secret_access_key|api[_-]?key|client_secret|access_token)\s*[:=]\s*['\"]?[A-Za-z0-9_./+\-=]{12,})"
)


@dataclass(slots=True)
class Passage:
    path: str
    start_line: int
    end_line: int
    score: float
    text: str

    def to_dict(self):
        return asdict(self)


@dataclass(slots=True)
class RetrievalStats:
    files_considered: int = 0
    files_scanned: int = 0
    bytes_scanned: int = 0
    files_skipped_ignored: int = 0
    files_skipped_sensitive: int = 0
    files_skipped_symlink: int = 0
    limit_reached: bool = False
    gitignore_applied: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass(slots=True)
class RetrievalResult:
    passages: list[Passage]
    stats: RetrievalStats


def _is_probably_text(sample: bytes) -> bool:
    return b"\x00" not in sample


def _is_sensitive_path(path: Path, root: Path, config: dict) -> bool:
    rel = path.relative_to(root).as_posix()
    name = path.name
    if name in set(config["exclude_files"]):
        return True
    return any(fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel, pattern) for pattern in config.get("exclude_globs", []))


def _candidate_paths(root: Path, config: dict, stats: RetrievalStats) -> list[Path]:
    excluded_dirs = set(config["exclude_dirs"])
    allowed = set(config["allowed_extensions"])
    max_bytes = int(config["max_file_bytes"])
    max_files = int(config["max_files_scanned"])
    candidates: list[Path] = []

    for current, dirs, names in os.walk(root, followlinks=False):
        current_path = Path(current)
        kept_dirs = []
        for name in sorted(dirs):
            candidate = current_path / name
            if name in excluded_dirs:
                continue
            if candidate.is_symlink():
                stats.files_skipped_symlink += 1
                continue
            kept_dirs.append(name)
        dirs[:] = kept_dirs

        for name in sorted(names):
            path = current_path / name
            if path.is_symlink():
                stats.files_skipped_symlink += 1
                continue
            if path.suffix.lower() not in allowed:
                continue
            if _is_sensitive_path(path, root, config):
                stats.files_skipped_sensitive += 1
                continue
            if stats.files_considered >= max_files:
                stats.limit_reached = True
                return candidates
            stats.files_considered += 1
            try:
                resolved = path.resolve(strict=True)
                if not resolved.is_relative_to(root) or not resolved.is_file() or resolved.stat().st_size > max_bytes:
                    continue
            except OSError:
                continue
            candidates.append(resolved)
    return candidates


def _git_ignored(root: Path, paths: list[Path], stats: RetrievalStats) -> set[Path]:
    if not paths:
        return set()
    try:
        probe = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True,
            check=True,
            text=True,
        )
        git_root = Path(probe.stdout.strip()).resolve()
        rels = [path.relative_to(git_root).as_posix() for path in paths]
        checked = subprocess.run(
            ["git", "-C", str(git_root), "check-ignore", "--stdin", "-z"],
            input=("\0".join(rels) + "\0").encode(),
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        if (root / ".gitignore").is_file():
            raise ValueError("Cannot enforce .gitignore because Git is unavailable") from exc
        return set()
    except (subprocess.CalledProcessError, ValueError):
        if (root / ".gitignore").is_file():
            raise ValueError(f"Cannot enforce ignore rules outside a Git worktree: {root}")
        return set()

    if checked.returncode not in {0, 1}:
        raise ValueError(f"git check-ignore failed for retrieval root: {root}")
    stats.gitignore_applied = True
    ignored_rels = [item.decode(errors="surrogateescape") for item in checked.stdout.split(b"\0") if item]
    return {(git_root / rel).resolve() for rel in ignored_rels}


def iter_candidate_files(root: Path, config: dict, stats: RetrievalStats | None = None) -> Iterable[Path]:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"Retrieval root is not a directory: {root}")
    stats = stats or RetrievalStats()
    candidates = _candidate_paths(root, config, stats)
    ignored = _git_ignored(root, candidates, stats)
    stats.files_skipped_ignored += len(ignored)
    for path in candidates:
        if path not in ignored:
            yield path


def _line_scores(query: str, lines: list[str]) -> list[tuple[float, int]]:
    q_terms = set(terms(query))
    scores = []
    for i, line in enumerate(lines):
        line_terms = set(terms(line))
        overlap = len(q_terms & line_terms) / max(1, len(q_terms))
        scores.append((overlap, i))
    return scores


def retrieve_with_stats(
    root: str | Path,
    query: str,
    config: dict,
    top_files: int | None = None,
    passages_per_file: int | None = None,
    context_lines: int | None = None,
) -> RetrievalResult:
    root_path = Path(root).resolve(strict=True)
    file_limit = int(top_files if top_files is not None else config["top_files"])
    passage_limit = int(passages_per_file if passages_per_file is not None else config["passages_per_file"])
    selected_context_lines = int(context_lines if context_lines is not None else config["passage_context_lines"])
    if file_limit < 1 or passage_limit < 1 or selected_context_lines < 0:
        raise ValueError("top-files and passages-per-file must be positive; context-lines cannot be negative")

    preview_limit = int(config["max_preview_bytes"])
    byte_limit = int(config["max_total_bytes_scanned"])
    stats = RetrievalStats()
    ranked: list[tuple[float, str, Path]] = []

    for path in iter_candidate_files(root_path, config, stats):
        if stats.bytes_scanned >= byte_limit:
            stats.limit_reached = True
            break
        read_limit = min(preview_limit, byte_limit - stats.bytes_scanned)
        try:
            with path.open("rb") as handle:
                sample = handle.read(read_limit)
        except OSError:
            continue
        stats.files_scanned += 1
        stats.bytes_scanned += len(sample)
        if not _is_probably_text(sample):
            continue
        preview = sample.decode("utf-8", errors="replace")
        if SENSITIVE_CONTENT.search(preview):
            stats.files_skipped_sensitive += 1
            continue
        rel_path = str(path.relative_to(root_path))
        score = 0.35 * lexical_relevance(query, rel_path) + 0.65 * lexical_relevance(query, preview)
        if score <= 0:
            continue
        item = (score, rel_path, path)
        if len(ranked) < file_limit:
            heapq.heappush(ranked, item)
        elif item > ranked[0]:
            heapq.heapreplace(ranked, item)

    max_chars = int(config["max_passage_chars"])
    results: list[Passage] = []

    for file_score, rel_path, path in sorted(ranked, reverse=True):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()
        ranked_lines = sorted(_line_scores(query, lines), reverse=True)
        selected: list[tuple[int, int]] = []

        for line_score, index in ranked_lines:
            if line_score <= 0 and selected:
                break
            start = max(0, index - selected_context_lines)
            end = min(len(lines), index + selected_context_lines + 1)
            if any(not (end <= a or start >= b) for a, b in selected):
                continue
            selected.append((start, end))
            if len(selected) >= passage_limit:
                break

        if not selected and lines:
            selected = [(0, min(len(lines), selected_context_lines * 2 + 1))]

        for start, end in sorted(selected):
            passage_text = "\n".join(lines[start:end])
            if len(passage_text) > max_chars:
                passage_text = passage_text[:max_chars] + "\n[…truncated]"
            local_score = lexical_relevance(query, passage_text)
            results.append(Passage(
                path=rel_path,
                start_line=start + 1,
                end_line=end,
                score=round(0.5 * file_score + 0.5 * local_score, 4),
                text=passage_text,
            ))

    results.sort(key=lambda passage: passage.score, reverse=True)
    return RetrievalResult(passages=results, stats=stats)


def retrieve(
    root: str | Path,
    query: str,
    config: dict,
    top_files: int | None = None,
    passages_per_file: int | None = None,
    context_lines: int | None = None,
) -> list[Passage]:
    return retrieve_with_stats(root, query, config, top_files, passages_per_file, context_lines).passages
