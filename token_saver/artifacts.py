from __future__ import annotations

import hashlib
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

from .state import StateDB


STATUSES = {"candidate", "accepted", "superseded", "rejected", "archived"}


class ArtifactStore:
    def __init__(self, state_dir: str | Path = ".token-saver", scope: str = "default"):
        self.db = StateDB(state_dir)
        self.scope = scope
        self.artifact_dir = self.db.root / "artifacts"
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.artifact_dir, 0o700)

    @staticmethod
    def _record(row) -> dict[str, Any]:
        return dict(row)

    def add(self, path: str | Path, label: str = "default") -> dict[str, Any]:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(source)
        content = source.read_bytes()
        artifact_id = uuid.uuid4().hex[:12]
        target = self.artifact_dir / f"{artifact_id}-{source.name}"
        shutil.copy2(source, target)
        os.chmod(target, 0o600)
        now = int(time.time())
        try:
            with self.db.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO artifacts(
                        id, scope, label, status, source_path, stored_path,
                        sha256, size, created_at, accepted_at
                    ) VALUES (?, ?, ?, 'candidate', ?, ?, ?, ?, ?, NULL)
                    """,
                    (
                        artifact_id, self.scope, label, str(source.resolve()), str(target.resolve()),
                        hashlib.sha256(content).hexdigest(), len(content), now,
                    ),
                )
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return self.get(artifact_id)

    def get(self, artifact_id: str) -> dict[str, Any]:
        connection = self.db.connect()
        try:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE id=? AND scope=?",
                (artifact_id, self.scope),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise KeyError(f"Unknown artifact id in scope {self.scope!r}: {artifact_id}")
        return self._record(row)

    def accept(self, artifact_id: str) -> dict[str, Any]:
        now = int(time.time())
        with self.db.transaction() as connection:
            selected = connection.execute(
                "SELECT * FROM artifacts WHERE id=? AND scope=?",
                (artifact_id, self.scope),
            ).fetchone()
            if selected is None:
                raise KeyError(f"Unknown artifact id in scope {self.scope!r}: {artifact_id}")
            connection.execute(
                "UPDATE artifacts SET status='superseded' WHERE scope=? AND label=? AND status='accepted'",
                (self.scope, selected["label"]),
            )
            connection.execute(
                "UPDATE artifacts SET status='accepted', accepted_at=? WHERE id=?",
                (now, artifact_id),
            )
        return self.get(artifact_id)

    def set_status(self, artifact_id: str, status: str) -> dict[str, Any]:
        if status not in STATUSES - {"accepted", "superseded"}:
            raise ValueError(f"Unsupported direct artifact status: {status}")
        with self.db.transaction() as connection:
            cursor = connection.execute(
                "UPDATE artifacts SET status=?, accepted_at=NULL WHERE id=? AND scope=?",
                (status, artifact_id, self.scope),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Unknown artifact id in scope {self.scope!r}: {artifact_id}")
        return self.get(artifact_id)

    def list(self, accepted_only: bool = False) -> list[dict[str, Any]]:
        query = "SELECT * FROM artifacts WHERE scope=?"
        params: tuple[Any, ...] = (self.scope,)
        if accepted_only:
            query += " AND status='accepted'"
        query += " ORDER BY created_at DESC, id DESC"
        connection = self.db.connect()
        try:
            return [self._record(row) for row in connection.execute(query, params).fetchall()]
        finally:
            connection.close()
