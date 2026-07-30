from __future__ import annotations

import copy
import os
import tomllib
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PACKAGE_ROOT / "config" / "default.toml"


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    with DEFAULT_CONFIG.open("rb") as handle:
        config = tomllib.load(handle)

    override_path = Path(path or os.getenv("TOKEN_SAVER_CONFIG", "")).expanduser()
    if str(override_path) not in {"", "."} and override_path.exists():
        with override_path.open("rb") as handle:
            config = _merge(config, tomllib.load(handle))
    return config


def resolve_mode(config: dict[str, Any], mode: str | None = None) -> tuple[str, dict[str, Any]]:
    selected = mode or os.getenv("TOKEN_SAVER_MODE") or config["default_mode"]
    if selected not in config["modes"]:
        choices = ", ".join(sorted(config["modes"]))
        raise ValueError(f"Unknown mode {selected!r}; choose one of: {choices}")
    merged = dict(config["common"])
    merged.update(config["modes"][selected])
    return selected, merged
