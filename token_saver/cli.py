from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from pathlib import Path

from .artifacts import ArtifactStore
from .compaction import compact
from .config import load_config, resolve_mode
from .metrics import compact_metrics, metric_line
from .models import ContextChunk
from .output_guard import validate_output
from .retrieval import retrieve
from .retry_guard import RetryGuard
from .router import recommend_tier


def _json_dump(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def _read_input(path: str) -> dict:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cmd_doctor(args) -> int:
    config = load_config(args.config)
    mode, policy = resolve_mode(config, args.mode)
    _json_dump({
        "ok": True,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "mode": mode,
        "context_budget_tokens": policy["context_budget_tokens"],
        "config": str(Path(args.config).resolve()) if args.config else "default",
        "state_dir": os.getenv("TOKEN_SAVER_STATE_DIR", config["state_dir"]),
    })
    return 0


def cmd_route(args) -> int:
    result = recommend_tier(args.request, args.file_count, args.high_stakes)
    _json_dump({"tier": result.tier, "score": result.score, "reasons": result.reasons})
    return 0


def cmd_retrieve(args) -> int:
    config = load_config(args.config)
    mode, policy = resolve_mode(config, args.mode)
    passages = retrieve(args.root, args.query, policy, args.top_files, args.passages_per_file)
    payload = {
        "query": args.query,
        "root": str(Path(args.root).resolve()),
        "mode": mode,
        "passages": [passage.to_dict() for passage in passages],
    }
    _json_dump(payload)
    return 0


def cmd_compact(args) -> int:
    payload = _read_input(args.input)
    config = load_config(args.config)
    mode, policy = resolve_mode(config, args.mode or payload.get("mode"))
    chunks = [ContextChunk(**item) for item in payload.get("chunks", [])]
    result = compact(payload.get("request", ""), chunks, policy, mode, config["weights"])
    output = result.to_dict()
    output["metrics"] = compact_metrics(result)
    if args.metrics_line:
        output["metrics_line"] = metric_line(result)
    encoded = json.dumps(output, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(encoded + "\n", encoding="utf-8")
    else:
        print(encoded)
    return 0


def cmd_validate(args) -> int:
    text = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
    result = validate_output(
        text,
        exact_words=args.exact_words,
        max_words=args.max_words,
        exact_bullets=args.exact_bullets,
        require_json=args.json,
        required_headings=args.require_heading,
    )
    _json_dump(result.to_dict())
    return 0 if result.valid else 2


def _state_dir(config: dict) -> str:
    return os.getenv("TOKEN_SAVER_STATE_DIR", config["state_dir"])


def cmd_artifact(args) -> int:
    config = load_config(args.config)
    store = ArtifactStore(_state_dir(config))
    if args.artifact_command == "add":
        _json_dump(store.add(args.file, args.label))
    elif args.artifact_command == "accept":
        _json_dump(store.accept(args.id))
    elif args.artifact_command == "show":
        _json_dump(store.list(args.accepted))
    return 0


def cmd_retry(args) -> int:
    config = load_config(args.config)
    guard = RetryGuard(_state_dir(config))
    max_retries = args.max_retries or int(config["common"]["max_retries_same_signature"])
    result = guard.check(
        args.operation, args.error, max_retries=max_retries,
        input_hash=args.input_hash, strategy=args.strategy,
    )
    _json_dump(result)
    return 0 if result["allowed"] else 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="token-saver", description="Reduce agent context tokens without blindly sacrificing quality.")
    parser.add_argument("--config", help="Optional TOML override.")
    parser.add_argument("--mode", choices=["quality-first", "balanced", "extreme"])
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Show effective configuration.")
    doctor.set_defaults(func=cmd_doctor)

    route = sub.add_parser("route", help="Recommend a model tier.")
    route.add_argument("--request", required=True)
    route.add_argument("--file-count", type=int, default=0)
    route.add_argument("--high-stakes", action="store_true")
    route.set_defaults(func=cmd_route)

    retrieval = sub.add_parser("retrieve", help="Rank text files and extract narrow passages.")
    retrieval.add_argument("--root", default=".")
    retrieval.add_argument("--query", required=True)
    retrieval.add_argument("--top-files", type=int)
    retrieval.add_argument("--passages-per-file", type=int)
    retrieval.set_defaults(func=cmd_retrieve)

    comp = sub.add_parser("compact", help="Compact a JSON context bundle.")
    comp.add_argument("--input", required=True, help="Input JSON path or - for stdin.")
    comp.add_argument("--output")
    comp.add_argument("--metrics-line", action="store_true")
    comp.set_defaults(func=cmd_compact)

    val = sub.add_parser("validate-output", help="Validate output constraints.")
    val.add_argument("file", help="File path or - for stdin.")
    val.add_argument("--exact-words", type=int)
    val.add_argument("--max-words", type=int)
    val.add_argument("--exact-bullets", type=int)
    val.add_argument("--json", action="store_true")
    val.add_argument("--require-heading", action="append", default=[])
    val.set_defaults(func=cmd_validate)

    artifact = sub.add_parser("artifact", help="Manage accepted artifacts.")
    artifact_sub = artifact.add_subparsers(dest="artifact_command", required=True)
    add = artifact_sub.add_parser("add")
    add.add_argument("file")
    add.add_argument("--label", default="default")
    add.set_defaults(func=cmd_artifact)
    accept = artifact_sub.add_parser("accept")
    accept.add_argument("id")
    accept.set_defaults(func=cmd_artifact)
    show = artifact_sub.add_parser("show")
    show.add_argument("--accepted", action="store_true")
    show.set_defaults(func=cmd_artifact)

    retry = sub.add_parser("retry-check", help="Stop repeated identical failures.")
    retry.add_argument("--operation", required=True)
    retry.add_argument("--error", required=True)
    retry.add_argument("--input-hash", default="")
    retry.add_argument("--strategy", default="")
    retry.add_argument("--max-retries", type=int)
    retry.set_defaults(func=cmd_retry)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
        print(f"token-saver: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
