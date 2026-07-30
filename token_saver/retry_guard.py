from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path
from typing import Any

from .state import StateDB


VOLATILE = re.compile(r"\b(?:0x[0-9a-f]+|\d{2}:\d{2}:\d{2}(?:\.\d+)?|\d{4}-\d{2}-\d{2}[T ][^\s]+)\b", re.I)


def normalize_error(error: str) -> str:
    return " ".join(VOLATILE.sub("<volatile>", error).lower().split())


class RetryGuard:
    def __init__(self, state_dir: str | Path = ".token-saver", scope: str = "default"):
        self.db = StateDB(state_dir)
        self.scope = scope

    @staticmethod
    def signature(operation: str, error: str, input_hash: str = "", strategy: str = "") -> str:
        payload = "\n".join((operation.strip(), normalize_error(error), input_hash.strip(), strategy.strip()))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def check(
        self,
        operation: str,
        error: str,
        max_retries: int = 2,
        input_hash: str = "",
        strategy: str = "",
        ttl_seconds: int = 86400,
    ) -> dict[str, Any]:
        if max_retries < 0:
            raise ValueError("max_retries must be zero or greater")
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be positive")
        signature = self.signature(operation, error, input_hash, strategy)
        now = int(time.time())
        with self.db.transaction() as connection:
            connection.execute(
                "DELETE FROM retries WHERE scope=? AND last_seen < ?",
                (self.scope, now - ttl_seconds),
            )
            row = connection.execute(
                "SELECT count, first_seen FROM retries WHERE scope=? AND signature=?",
                (self.scope, signature),
            ).fetchone()
            count = int(row["count"]) + 1 if row else 1
            first_seen = int(row["first_seen"]) if row else now
            connection.execute(
                """
                INSERT INTO retries(scope, signature, count, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(scope, signature) DO UPDATE SET
                    count=excluded.count,
                    last_seen=excluded.last_seen
                """,
                (self.scope, signature, count, first_seen, now),
            )

        allowed = count <= max_retries
        return {
            "allowed": allowed,
            "scope": self.scope,
            "signature": signature[:16],
            "attempt": count,
            "max_retries": max_retries,
            "expires_after_seconds": ttl_seconds,
            "action": "retry" if allowed else "stop_or_change_strategy",
        }

    def reset(self, signature: str | None = None) -> int:
        with self.db.transaction() as connection:
            if signature:
                cursor = connection.execute(
                    "DELETE FROM retries WHERE scope=? AND signature LIKE ?",
                    (self.scope, f"{signature}%"),
                )
            else:
                cursor = connection.execute("DELETE FROM retries WHERE scope=?", (self.scope,))
        return cursor.rowcount
