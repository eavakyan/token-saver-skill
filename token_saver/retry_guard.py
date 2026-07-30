from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

VOLATILE = re.compile(r"\b(?:0x[0-9a-f]+|\d{2}:\d{2}:\d{2}(?:\.\d+)?|\d{4}-\d{2}-\d{2}[T ][^\s]+)\b", re.I)


def normalize_error(error: str) -> str:
    return " ".join(VOLATILE.sub("<volatile>", error).lower().split())


class RetryGuard:
    def __init__(self, state_dir: str | Path = ".token-saver"):
        self.root = Path(state_dir)
        self.path = self.root / "retries.json"

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"signatures": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        temp.replace(self.path)

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
    ) -> dict[str, Any]:
        signature = self.signature(operation, error, input_hash, strategy)
        data = self._load()
        record = data["signatures"].get(signature, {"count": 0, "first_seen": int(time.time())})
        record["count"] += 1
        record["last_seen"] = int(time.time())
        data["signatures"][signature] = record
        self._save(data)

        allowed = record["count"] <= max_retries
        return {
            "allowed": allowed,
            "signature": signature[:16],
            "attempt": record["count"],
            "max_retries": max_retries,
            "action": "retry" if allowed else "stop_or_change_strategy",
        }
