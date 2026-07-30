from __future__ import annotations

import hashlib
import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Any


class ArtifactStore:
    def __init__(self, state_dir: str | Path = ".token-saver"):
        self.root = Path(state_dir)
        self.artifact_dir = self.root / "artifacts"
        self.index_path = self.root / "artifacts.json"
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {"artifacts": []}
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        temp = self.index_path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        temp.replace(self.index_path)

    def add(self, path: str | Path, label: str = "default") -> dict[str, Any]:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(source)
        content = source.read_bytes()
        artifact_id = uuid.uuid4().hex[:12]
        target = self.artifact_dir / f"{artifact_id}-{source.name}"
        shutil.copy2(source, target)
        record = {
            "id": artifact_id,
            "label": label,
            "status": "candidate",
            "source_path": str(source.resolve()),
            "stored_path": str(target.resolve()),
            "sha256": hashlib.sha256(content).hexdigest(),
            "size": len(content),
            "created_at": int(time.time()),
        }
        data = self._load()
        data["artifacts"].append(record)
        self._save(data)
        return record

    def accept(self, artifact_id: str) -> dict[str, Any]:
        data = self._load()
        selected = None
        for record in data["artifacts"]:
            if record["id"] == artifact_id:
                selected = record
                break
        if selected is None:
            raise KeyError(f"Unknown artifact id: {artifact_id}")

        for record in data["artifacts"]:
            if record["label"] == selected["label"] and record["status"] == "accepted":
                record["status"] = "superseded"
        selected["status"] = "accepted"
        selected["accepted_at"] = int(time.time())
        self._save(data)
        return selected

    def list(self, accepted_only: bool = False) -> list[dict[str, Any]]:
        records = self._load()["artifacts"]
        if accepted_only:
            records = [record for record in records if record["status"] == "accepted"]
        return sorted(records, key=lambda record: record["created_at"], reverse=True)
