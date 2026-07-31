from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    label TEXT NOT NULL,
    status TEXT NOT NULL,
    source_path TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    accepted_at INTEGER
);
CREATE INDEX IF NOT EXISTS artifacts_scope_status ON artifacts(scope, status, created_at);
CREATE TABLE IF NOT EXISTS retries (
    scope TEXT NOT NULL,
    signature TEXT NOT NULL,
    count INTEGER NOT NULL,
    first_seen INTEGER NOT NULL,
    last_seen INTEGER NOT NULL,
    PRIMARY KEY (scope, signature)
);
CREATE TABLE IF NOT EXISTS handoffs (
    scope TEXT PRIMARY KEY,
    document_json TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    command TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    mode TEXT,
    model TEXT,
    tokenizer TEXT,
    status TEXT,
    estimated_tokens_before INTEGER,
    estimated_tokens_after INTEGER,
    estimated_tokens_avoided INTEGER,
    estimated_savings_percent REAL,
    minimum_required_tokens INTEGER,
    actions_json TEXT NOT NULL,
    warnings_json TEXT NOT NULL,
    provider_usage_json TEXT,
    metadata_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS runs_scope_created ON runs(scope, created_at);
"""


class StateDB:
    def __init__(self, state_dir: str | Path):
        self.root = Path(state_dir).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.path = self.root / "state.sqlite3"
        connection = self.connect()
        try:
            connection.executescript(SCHEMA)
        finally:
            connection.close()
        os.chmod(self.path, 0o600)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


class HandoffStore:
    def __init__(self, state_dir: str | Path):
        self.db = StateDB(state_dir)

    def save(self, scope: str, document: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(document, dict):
            raise ValueError("Handoff must be a JSON object")
        now = int(time.time())
        encoded = json.dumps(document, ensure_ascii=False, sort_keys=True)
        with self.db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO handoffs(scope, document_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(scope) DO UPDATE SET
                    document_json=excluded.document_json,
                    updated_at=excluded.updated_at
                """,
                (scope, encoded, now, now),
            )
        return self.show(scope) or {}

    def show(self, scope: str) -> dict[str, Any] | None:
        connection = self.db.connect()
        try:
            row = connection.execute(
                "SELECT scope, document_json, created_at, updated_at FROM handoffs WHERE scope=?",
                (scope,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        return {
            "scope": row["scope"],
            "document": json.loads(row["document_json"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def clear(self, scope: str) -> bool:
        with self.db.transaction() as connection:
            cursor = connection.execute("DELETE FROM handoffs WHERE scope=?", (scope,))
        return bool(cursor.rowcount)


class RunStore:
    """Append-only local telemetry for Token Saver operations.

    Only derived metrics and caller-supplied usage metadata are persisted. Raw
    requests, context chunks, and discarded text are intentionally excluded.
    """

    def __init__(self, state_dir: str | Path):
        self.db = StateDB(state_dir)

    def record(
        self,
        scope: str,
        command: str,
        metrics: dict[str, Any] | None = None,
        *,
        run_id: str | None = None,
        model: str | None = None,
        tokenizer: str | None = None,
        provider_usage: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metrics = metrics or {}
        run_id = run_id or uuid.uuid4().hex
        created_at = int(time.time())
        record = {
            "id": run_id,
            "scope": scope,
            "command": command,
            "created_at": created_at,
            "mode": metrics.get("mode"),
            "model": model,
            "tokenizer": tokenizer,
            "status": metrics.get("status"),
            "estimated_tokens_before": metrics.get("estimated_tokens_before"),
            "estimated_tokens_after": metrics.get("estimated_tokens_after"),
            "estimated_tokens_avoided": metrics.get("estimated_tokens_avoided"),
            "estimated_savings_percent": metrics.get("estimated_savings_percent"),
            "minimum_required_tokens": metrics.get("minimum_required_tokens"),
            "actions": metrics.get("actions", {}),
            "warnings": metrics.get("warnings", []),
            "provider_usage": provider_usage,
            "metadata": metadata or {},
        }
        with self.db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO runs(
                    id, scope, command, created_at, mode, model, tokenizer,
                    status, estimated_tokens_before, estimated_tokens_after,
                    estimated_tokens_avoided, estimated_savings_percent,
                    minimum_required_tokens, actions_json, warnings_json,
                    provider_usage_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id, scope, command, created_at, record["mode"], model,
                    tokenizer, record["status"], record["estimated_tokens_before"],
                    record["estimated_tokens_after"], record["estimated_tokens_avoided"],
                    record["estimated_savings_percent"], record["minimum_required_tokens"],
                    json.dumps(record["actions"], sort_keys=True),
                    json.dumps(record["warnings"], ensure_ascii=False),
                    json.dumps(provider_usage, sort_keys=True) if provider_usage is not None else None,
                    json.dumps(record["metadata"], sort_keys=True),
                ),
            )
        return record

    def start_request(self, scope: str) -> dict[str, Any]:
        """Create an isolated telemetry envelope for one skill invocation."""
        request_id = uuid.uuid4().hex
        return self.record(
            scope,
            "request",
            {"status": "started"},
            run_id=request_id,
            metadata={"request_id": request_id},
        )

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "scope": row["scope"],
            "command": row["command"],
            "created_at": row["created_at"],
            "mode": row["mode"],
            "model": row["model"],
            "tokenizer": row["tokenizer"],
            "status": row["status"],
            "estimated_tokens_before": row["estimated_tokens_before"],
            "estimated_tokens_after": row["estimated_tokens_after"],
            "estimated_tokens_avoided": row["estimated_tokens_avoided"],
            "estimated_savings_percent": row["estimated_savings_percent"],
            "minimum_required_tokens": row["minimum_required_tokens"],
            "actions": json.loads(row["actions_json"]),
            "warnings": json.loads(row["warnings_json"]),
            "provider_usage": json.loads(row["provider_usage_json"]) if row["provider_usage_json"] else None,
            "metadata": json.loads(row["metadata_json"]),
        }

    def list(self, scope: str, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 1000))
        connection = self.db.connect()
        try:
            rows = connection.execute(
                "SELECT * FROM runs WHERE scope=? ORDER BY created_at DESC, id DESC LIMIT ?",
                (scope, limit),
            ).fetchall()
        finally:
            connection.close()
        return [self._decode(row) for row in rows]

    def show(self, run_id: str, scope: str | None = None) -> dict[str, Any] | None:
        connection = self.db.connect()
        try:
            if scope:
                row = connection.execute("SELECT * FROM runs WHERE id=? AND scope=?", (run_id, scope)).fetchone()
            else:
                row = connection.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        finally:
            connection.close()
        return self._decode(row) if row else None

    def summary(self, scope: str) -> dict[str, Any]:
        connection = self.db.connect()
        try:
            rows = connection.execute("SELECT * FROM runs WHERE scope=? ORDER BY created_at ASC, id ASC", (scope,)).fetchall()
        finally:
            connection.close()
        records = [self._decode(row) for row in rows]
        before = sum(record["estimated_tokens_before"] or 0 for record in records)
        after = sum(record["estimated_tokens_after"] or 0 for record in records)
        avoided = max(0, before - after)
        statuses: dict[str, int] = {}
        actions: dict[str, int] = {}
        provider_totals: dict[str, float] = {}
        for record in records:
            statuses[record["status"] or "unknown"] = statuses.get(record["status"] or "unknown", 0) + 1
            for action, count in record["actions"].items():
                actions[action] = actions.get(action, 0) + int(count)
            if record["provider_usage"]:
                for key in ("input_tokens", "output_tokens", "cached_input_tokens", "total_tokens", "cost_usd"):
                    value = record["provider_usage"].get(key)
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        provider_totals[key] = provider_totals.get(key, 0) + value
        return {
            "scope": scope,
            "runs": len(records),
            "compaction_runs": sum(record["command"] == "compact" for record in records),
            "estimated_tokens_before": before,
            "estimated_tokens_after": after,
            "estimated_tokens_avoided": avoided,
            "estimated_savings_percent": round(avoided / before * 100, 1) if before else 0.0,
            "statuses": statuses,
            "actions": actions,
            "provider_usage_available": any(record["provider_usage"] is not None for record in records),
            "provider_usage_totals": provider_totals,
        }

    def request_report(self, request_id: str, scope: str) -> dict[str, Any] | None:
        """Return telemetry for exactly one invocation, never a scope-wide latest run."""
        connection = self.db.connect()
        try:
            rows = connection.execute(
                "SELECT * FROM runs WHERE scope=? ORDER BY created_at ASC, id ASC",
                (scope,),
            ).fetchall()
        finally:
            connection.close()
        records = [self._decode(row) for row in rows]
        request = next(
            (
                record for record in records
                if record["id"] == request_id
                and record["command"] == "request"
                and record["metadata"].get("request_id") == request_id
            ),
            None,
        )
        if request is None:
            return None
        operations = [
            record for record in records
            if record["id"] != request_id and record["metadata"].get("request_id") == request_id
        ]
        operation_counts: dict[str, int] = {}
        statuses: dict[str, int] = {}
        retrieval_stats = {
            "files_considered": 0,
            "files_scanned": 0,
            "bytes_scanned": 0,
            "files_skipped_ignored": 0,
            "files_skipped_sensitive": 0,
            "files_skipped_symlink": 0,
            "limit_reached": False,
            "gitignore_applied": False,
        }
        retrieval_runs = 0
        passages_returned = 0
        compact_before = 0
        compact_after = 0
        provider_totals: dict[str, float] = {}
        provider_usage_available = False

        for record in operations:
            command = record["command"]
            operation_counts[command] = operation_counts.get(command, 0) + 1
            status = record["status"] or "unknown"
            statuses[status] = statuses.get(status, 0) + 1
            if command == "retrieve":
                retrieval_runs += 1
                passages_returned += int(record["metadata"].get("passages_returned", 0))
                stats = record["metadata"].get("stats", {})
                if isinstance(stats, dict):
                    for key in (
                        "files_considered", "files_scanned", "bytes_scanned",
                        "files_skipped_ignored", "files_skipped_sensitive", "files_skipped_symlink",
                    ):
                        value = stats.get(key)
                        if isinstance(value, int) and not isinstance(value, bool):
                            retrieval_stats[key] += value
                    for key in ("limit_reached", "gitignore_applied"):
                        retrieval_stats[key] = retrieval_stats[key] or bool(stats.get(key))
            if command == "compact":
                compact_before += int(record["estimated_tokens_before"] or 0)
                compact_after += int(record["estimated_tokens_after"] or 0)
            if record["provider_usage"]:
                provider_usage_available = True
                for key in ("input_tokens", "output_tokens", "cached_input_tokens", "total_tokens", "cost_usd"):
                    value = record["provider_usage"].get(key)
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        provider_totals[key] = provider_totals.get(key, 0) + value

        compact_avoided = max(0, compact_before - compact_after)
        return {
            "request_id": request_id,
            "scope": scope,
            "started_at": request["created_at"],
            "operations": operation_counts,
            "statuses": statuses,
            "retrieval": {
                "runs": retrieval_runs,
                "passages_returned": passages_returned,
                **retrieval_stats,
            },
            "compaction": {
                "runs": operation_counts.get("compact", 0),
                "estimated_tokens_before": compact_before,
                "estimated_tokens_after": compact_after,
                "estimated_tokens_avoided": compact_avoided,
                "estimated_savings_percent": round(compact_avoided / compact_before * 100, 1) if compact_before else 0.0,
            },
            "provider_usage_available": provider_usage_available,
            "provider_usage_totals": provider_totals,
        }

    def export_jsonl(self, scope: str) -> str:
        connection = self.db.connect()
        try:
            rows = connection.execute("SELECT * FROM runs WHERE scope=? ORDER BY created_at ASC, id ASC", (scope,)).fetchall()
        finally:
            connection.close()
        return "".join(json.dumps(self._decode(row), ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
