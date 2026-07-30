#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL_SOURCE = (ROOT / "skill").resolve()
with (ROOT / "pyproject.toml").open("rb") as version_file:
    EXPECTED_CLI_VERSION = tomllib.load(version_file)["project"]["version"]
BEGIN = "<!-- TOKEN-SAVER:BEGIN -->"
END = "<!-- TOKEN-SAVER:END -->"
SHIM = """<!-- TOKEN-SAVER:BEGIN -->
## Token Saver

For explicitly token-constrained or genuinely large, retrieval-heavy work, invoke `$token-saver`. Preserve constraints, decisions, accepted artifacts, and essential evidence; do not optimize routine requests with the full workflow.
<!-- TOKEN-SAVER:END -->"""


def upsert_block(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if BEGIN in existing and END in existing:
        start = existing.index(BEGIN)
        end = existing.index(END, start) + len(END)
        updated = existing[:start].rstrip() + "\n\n" + SHIM + "\n" + existing[end:].lstrip()
    else:
        updated = existing.rstrip() + ("\n\n" if existing.strip() else "") + SHIM + "\n"
    temporary = path.with_name(f".{path.name}.token-saver.tmp")
    temporary.write_text(updated, encoding="utf-8")
    os.replace(temporary, path)


def destinations(platform: str, scope: str, project: Path):
    home = Path.home()
    result = []
    if platform in {"claude", "all"}:
        skill = home / ".claude/skills/token-saver" if scope == "global" else project / ".claude/skills/token-saver"
        instructions = home / ".claude/CLAUDE.md" if scope == "global" else project / "CLAUDE.md"
        result.append(("claude", skill, instructions))
    if platform in {"codex", "all"}:
        skill = home / ".agents/skills/token-saver" if scope == "global" else project / ".agents/skills/token-saver"
        instructions = home / ".codex/AGENTS.md" if scope == "global" else project / "AGENTS.md"
        result.append(("codex", skill, instructions))
    return result


def install_symlink(target: Path, force: bool) -> tuple[str, Path | None]:
    if target.is_symlink() and target.resolve(strict=False) == SKILL_SOURCE:
        return "already linked", None
    backup = None
    if target.exists() or target.is_symlink():
        if not force:
            raise FileExistsError(f"{target} exists; rerun with --force to move it aside safely")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = target.with_name(f"{target.name}.backup-{stamp}")
        if backup.exists() or backup.is_symlink():
            raise FileExistsError(f"Backup target already exists: {backup}")
        target.rename(backup)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(SKILL_SOURCE, target_is_directory=True)
    return "linked", backup


def verify_cli() -> None:
    executable = shutil.which("token-saver")
    if executable is None:
        raise SystemExit("token-saver is not on PATH; install the CLI first or use --skip-cli-check for staged setup")
    result = subprocess.run([executable, "doctor"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise SystemExit(f"token-saver doctor failed: {result.stderr.strip() or result.stdout.strip()}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit("token-saver doctor returned invalid JSON") from exc
    if payload.get("version") != EXPECTED_CLI_VERSION:
        raise SystemExit(
            f"token-saver CLI version {payload.get('version')!r} does not match required {EXPECTED_CLI_VERSION}; reinstall this repository"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Symlink the canonical Token Saver skill into supported discovery locations.")
    parser.add_argument("--platform", choices=["claude", "codex", "all"], default="codex")
    parser.add_argument("--scope", choices=["global", "project"], default="global")
    parser.add_argument("--project", default=".")
    parser.add_argument("--always-on", action="store_true", help="Add the optional compact conditional instruction shim.")
    parser.add_argument("--force", action="store_true", help="Move an existing target to a timestamped backup before linking.")
    parser.add_argument("--skip-cli-check", action="store_true", help="Allow linking before the token-saver console command is installed.")
    args = parser.parse_args()

    if not args.skip_cli_check:
        verify_cli()
    if not (SKILL_SOURCE / "SKILL.md").is_file():
        raise SystemExit(f"Canonical skill is incomplete: {SKILL_SOURCE}")

    project = Path(args.project).resolve()
    for name, target, instructions in destinations(args.platform, args.scope, project):
        try:
            action, backup = install_symlink(target, args.force)
        except FileExistsError as exc:
            raise SystemExit(str(exc)) from exc
        print(f"{name}: {action} {target} -> {SKILL_SOURCE}")
        if backup:
            print(f"Preserved previous target at: {backup}")
        if args.always_on:
            upsert_block(instructions)
            print(f"Updated optional instructions: {instructions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
