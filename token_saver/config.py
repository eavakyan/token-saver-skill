from __future__ import annotations

import copy
import os
import tomllib
from importlib.resources import files
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = files("token_saver").joinpath("data/default.toml")


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

    selected = path or os.getenv("TOKEN_SAVER_CONFIG")
    if selected:
        override_path = Path(selected).expanduser()
        if not override_path.is_file():
            raise FileNotFoundError(f"Configuration file not found: {override_path}")
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
