from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from .artifacts import ArtifactStore
from . import __version__
from .compaction import compact
from .config import load_config, resolve_mode
from .metrics import compact_metrics, metric_line
from .models import ContextChunk
from .output_guard import validate_output
from .retrieval import retrieve_with_stats
from .retry_guard import RetryGuard
from .router import recommend_tier
from .state import HandoffStore, RunStore


def _json_dump(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def _read_input(path: str) -> dict:
    if path == "-":
        value = json.load(sys.stdin)
    else:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Input JSON must be an object")
    return value


def _git_value(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args], capture_output=True, check=True, text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _project_root() -> Path:
    value = _git_value("rev-parse", "--show-toplevel")
    return Path(value).resolve() if value else Path.cwd().resolve()


def _state_dir(config: dict) -> Path:
    selected = Path(os.getenv("TOKEN_SAVER_STATE_DIR", config["state_dir"])).expanduser()
    return selected.resolve() if selected.is_absolute() else (_project_root() / selected).resolve()


def _state_scope(explicit: str | None = None) -> str:
    configured = explicit or os.getenv("TOKEN_SAVER_SCOPE")
    if configured:
        return configured
    branch = _git_value("branch", "--show-current") or _git_value("rev-parse", "--short", "HEAD") or "default"
    return f"{_project_root().name}:{branch}"


def _request_metadata(args) -> dict:
    request_id = getattr(args, "request_id", None) or os.getenv("TOKEN_SAVER_REQUEST_ID")
    return {"request_id": request_id} if request_id else {}


def _write_text_atomic(path: str | Path, text: str) -> None:
    target = Path(path)
    if not target.parent.exists():
        raise FileNotFoundError(f"Output directory not found: {target.parent}")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def cmd_doctor(args) -> int:
    config = load_config(args.config)
    mode, policy = resolve_mode(config, args.mode)
    _json_dump({
        "ok": True,
        "version": __version__,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "executable": shutil.which("token-saver"),
        "mode": mode,
        "context_budget_tokens": policy["context_budget_tokens"],
        "config": str(Path(args.config).resolve()) if args.config else "packaged-default",
        "state_dir": str(_state_dir(config)),
        "state_scope": _state_scope(args.state_scope),
    })
    return 0


def cmd_route(args) -> int:
    result = recommend_tier(args.request, args.file_count, args.high_stakes)
    _json_dump({
        "tier": result.tier,
        "model": result.model,
        "reasoning_effort": result.reasoning_effort,
        "score": result.score,
        "reasons": result.reasons,
        "advisory": result.advisory,
    })
    return 0


def cmd_retrieve(args) -> int:
    config = load_config(args.config)
    mode, policy = resolve_mode(config, args.mode)
    result = retrieve_with_stats(
        args.root,
        args.query,
        policy,
        args.top_files,
        args.passages_per_file,
        args.context_lines,
    )
    output = {
        "query": args.query,
        "root": str(Path(args.root).resolve()),
        "mode": mode,
        "stats": result.stats.to_dict(),
        "passages": [passage.to_dict() for passage in result.passages],
    }
    if not args.no_record:
        metadata = {"stats": result.stats.to_dict(), "passages_returned": len(result.passages)}
        metadata.update(_request_metadata(args))
        run = RunStore(_state_dir(config)).record(
            _state_scope(args.state_scope),
            "retrieve",
            {"mode": mode, "status": "ok"},
            metadata=metadata,
        )
        output["run"] = {"id": run["id"], "recorded": True}
    else:
        output["run"] = {"recorded": False}
    _json_dump(output)
    return 0


def cmd_compact(args) -> int:
    payload = _read_input(args.input)
    config = load_config(args.config)
    mode, policy = resolve_mode(config, args.mode or payload.get("mode"))
    chunks = [ContextChunk(**item) for item in payload.get("chunks", [])]
    result = compact(
        payload.get("request", ""),
        chunks,
        policy,
        mode,
        config["weights"],
        model=args.model or payload.get("model"),
    )
    output = result.to_dict()
    output["metrics"] = compact_metrics(result)
    if args.metrics_line:
        output["metrics_line"] = metric_line(result)
    if not args.no_record:
        metadata = {"chunks": len(chunks)}
        metadata.update(_request_metadata(args))
        run = RunStore(_state_dir(config)).record(
            _state_scope(args.state_scope),
            "compact",
            output["metrics"],
            model=result.model,
            tokenizer=result.tokenizer,
            metadata=metadata,
        )
        output["run"] = {"id": run["id"], "recorded": True}
        output["metrics"]["run_id"] = run["id"]
    else:
        output["run"] = {"recorded": False}
    if args.save_handoff:
        saved = HandoffStore(_state_dir(config)).save(_state_scope(args.state_scope), output)
        output["handoff"] = {"scope": saved["scope"], "updated_at": saved["updated_at"]}
    encoded = json.dumps(output, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        _write_text_atomic(args.output, encoded)
    else:
        print(encoded, end="")
    return 4 if result.status == "infeasible" else 0


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


def cmd_artifact(args) -> int:
    config = load_config(args.config)
    store = ArtifactStore(_state_dir(config), _state_scope(args.state_scope))
    if args.artifact_command == "add":
        _json_dump(store.add(args.file, args.label))
    elif args.artifact_command == "accept":
        _json_dump(store.accept(args.id))
    elif args.artifact_command in {"reject", "archive"}:
        status = "rejected" if args.artifact_command == "reject" else "archived"
        _json_dump(store.set_status(args.id, status))
    elif args.artifact_command == "show":
        _json_dump(store.list(args.accepted))
    return 0


def cmd_retry(args) -> int:
    config = load_config(args.config)
    guard = RetryGuard(_state_dir(config), _state_scope(args.state_scope))
    max_retries = args.max_retries if args.max_retries is not None else int(config["common"]["max_retries_same_signature"])
    ttl = args.ttl_seconds if args.ttl_seconds is not None else int(config["common"]["retry_ttl_seconds"])
    result = guard.check(
        args.operation,
        args.error,
        max_retries=max_retries,
        input_hash=args.input_hash,
        strategy=args.strategy,
        ttl_seconds=ttl,
    )
    _json_dump(result)
    return 0 if result["allowed"] else 3


def cmd_retry_reset(args) -> int:
    config = load_config(args.config)
    guard = RetryGuard(_state_dir(config), _state_scope(args.state_scope))
    _json_dump({"removed": guard.reset(args.signature), "scope": guard.scope})
    return 0


def cmd_handoff(args) -> int:
    config = load_config(args.config)
    scope = _state_scope(args.state_scope)
    store = HandoffStore(_state_dir(config))
    if args.handoff_command == "save":
        _json_dump(store.save(scope, _read_input(args.input)))
        return 0
    if args.handoff_command == "show":
        value = store.show(scope)
        if value is None:
            _json_dump({"scope": scope, "found": False})
            return 1
        _json_dump(value)
        return 0
    _json_dump({"scope": scope, "removed": store.clear(scope)})
    return 0


def _provider_usage(payload: dict) -> dict:
    source = payload.get("provider_usage", payload)
    if not isinstance(source, dict):
        raise ValueError("provider_usage must be a JSON object")
    allowed = {"provider", "model", "input_tokens", "output_tokens", "cached_input_tokens", "total_tokens", "cost_usd"}
    return {
        key: source[key]
        for key in allowed
        if key in source and isinstance(source[key], (str, int, float)) and not isinstance(source[key], bool)
    }


def cmd_metrics(args) -> int:
    config = load_config(args.config)
    scope = _state_scope(args.state_scope)
    store = RunStore(_state_dir(config))
    if args.metrics_command == "begin":
        run = store.start_request(scope)
        _json_dump({"request_id": run["id"], "scope": scope, "recorded": True})
        return 0
    if args.metrics_command == "report":
        value = store.request_report(args.request_id, scope)
        if value is None:
            _json_dump({"scope": scope, "found": False, "request_id": args.request_id})
            return 1
        _json_dump(value)
        return 0
    if args.metrics_command == "summary":
        _json_dump(store.summary(scope))
        return 0
    if args.metrics_command == "show":
        value = store.show(args.id, scope)
        if value is None:
            _json_dump({"scope": scope, "found": False, "id": args.id})
            return 1
        _json_dump(value)
        return 0
    if args.metrics_command == "export":
        encoded = store.export_jsonl(scope)
        if args.output:
            _write_text_atomic(args.output, encoded)
        else:
            print(encoded, end="")
        return 0

    payload = _read_input(args.input)
    usage = _provider_usage(payload)
    metadata = {"linked_run_id": payload["linked_run_id"]} if payload.get("linked_run_id") else {}
    metadata.update(_request_metadata(args))
    run = store.record(
        scope,
        "provider_usage",
        {"status": "reported"},
        model=usage.get("model"),
        provider_usage=usage,
        metadata=metadata,
    )
    _json_dump(run)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="token-saver", description="Reduce agent context tokens without blindly sacrificing quality.")
    parser.add_argument("--config", help="Optional TOML override; missing paths fail closed.")
    parser.add_argument("--mode", choices=["quality-first", "balanced", "extreme"])
    parser.add_argument("--state-scope", help="State namespace; defaults to repository and branch.")
    parser.add_argument("--request-id", help="Isolate telemetry for one Token Saver invocation; use with metrics begin/report.")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Show effective configuration and state location.")
    doctor.set_defaults(func=cmd_doctor)

    route = sub.add_parser("route", help="Recommend, but do not switch, a model tier.")
    route.add_argument("--request", required=True)
    route.add_argument("--file-count", type=int, default=0)
    route.add_argument("--high-stakes", action="store_true")
    route.set_defaults(func=cmd_route)

    retrieval = sub.add_parser("retrieve", help="Rank text files and extract narrow passages.")
    retrieval.add_argument("--root", default=".")
    retrieval.add_argument("--query", required=True)
    retrieval.add_argument("--top-files", type=int)
    retrieval.add_argument("--passages-per-file", type=int)
    retrieval.add_argument("--context-lines", type=int, help="Expand a promising hit without changing the query.")
    retrieval.add_argument("--no-record", action="store_true", help="Do not append local run telemetry.")
    retrieval.set_defaults(func=cmd_retrieve)

    comp = sub.add_parser("compact", help="Build a safe compact handoff from a JSON context bundle.")
    comp.add_argument("--input", required=True, help="Input JSON path or - for stdin.")
    comp.add_argument("--output")
    comp.add_argument("--metrics-line", action="store_true")
    comp.add_argument("--save-handoff", action="store_true")
    comp.add_argument("--model", help="Optional model name for tiktoken-based estimates when available.")
    comp.add_argument("--no-record", action="store_true", help="Do not append local run telemetry.")
    comp.set_defaults(func=cmd_compact)

    val = sub.add_parser("validate-output", help="Validate output constraints.")
    val.add_argument("file", help="File path or - for stdin.")
    val.add_argument("--exact-words", type=int)
    val.add_argument("--max-words", type=int)
    val.add_argument("--exact-bullets", type=int)
    val.add_argument("--json", action="store_true")
    val.add_argument("--require-heading", action="append", default=[])
    val.set_defaults(func=cmd_validate)

    artifact = sub.add_parser("artifact", help="Manage concurrency-safe accepted artifacts.")
    artifact_sub = artifact.add_subparsers(dest="artifact_command", required=True)
    add = artifact_sub.add_parser("add")
    add.add_argument("file")
    add.add_argument("--label", default="default")
    add.set_defaults(func=cmd_artifact)
    for command in ("accept", "reject", "archive"):
        action = artifact_sub.add_parser(command)
        action.add_argument("id")
        action.set_defaults(func=cmd_artifact)
    show = artifact_sub.add_parser("show")
    show.add_argument("--accepted", action="store_true")
    show.set_defaults(func=cmd_artifact)

    retry = sub.add_parser("retry-check", help="Stop repeated identical failures within a bounded scope and TTL.")
    retry.add_argument("--operation", required=True)
    retry.add_argument("--error", required=True)
    retry.add_argument("--input-hash", default="")
    retry.add_argument("--strategy", default="")
    retry.add_argument("--max-retries", type=int)
    retry.add_argument("--ttl-seconds", type=int)
    retry.set_defaults(func=cmd_retry)

    retry_reset = sub.add_parser("retry-reset", help="Reset retry signatures in the active state scope.")
    retry_reset.add_argument("--signature")
    retry_reset.set_defaults(func=cmd_retry_reset)

    handoff = sub.add_parser("handoff", help="Save, show, or clear a durable JSON handoff.")
    handoff_sub = handoff.add_subparsers(dest="handoff_command", required=True)
    handoff_save = handoff_sub.add_parser("save")
    handoff_save.add_argument("--input", required=True, help="JSON object path or - for stdin.")
    handoff_save.set_defaults(func=cmd_handoff)
    handoff_show = handoff_sub.add_parser("show")
    handoff_show.set_defaults(func=cmd_handoff)
    handoff_clear = handoff_sub.add_parser("clear")
    handoff_clear.set_defaults(func=cmd_handoff)

    metrics = sub.add_parser("metrics", help="Inspect append-only Token Saver run telemetry.")
    metrics_sub = metrics.add_subparsers(dest="metrics_command", required=True)
    metrics_begin = metrics_sub.add_parser("begin", help="Start an isolated telemetry envelope for this invocation.")
    metrics_begin.set_defaults(func=cmd_metrics)
    metrics_report = metrics_sub.add_parser("report", help="Report only the operations linked to one invocation.")
    metrics_report.add_argument("request_id")
    metrics_report.set_defaults(func=cmd_metrics)
    metrics_summary = metrics_sub.add_parser("summary")
    metrics_summary.set_defaults(func=cmd_metrics)
    metrics_show = metrics_sub.add_parser("show")
    metrics_show.add_argument("id")
    metrics_show.set_defaults(func=cmd_metrics)
    metrics_export = metrics_sub.add_parser("export")
    metrics_export.add_argument("--output")
    metrics_export.set_defaults(func=cmd_metrics)
    metrics_record = metrics_sub.add_parser("record", help="Record provider usage metadata supplied by the caller.")
    metrics_record.add_argument("--input", required=True, help="Provider usage JSON path or - for stdin.")
    metrics_record.set_defaults(func=cmd_metrics)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError, KeyError, json.JSONDecodeError, sqlite3.Error) as exc:
        print(f"token-saver: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
