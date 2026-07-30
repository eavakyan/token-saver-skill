from __future__ import annotations

import json
import os
import sqlite3
import time
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
