#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_SOURCE = ROOT / "skill"
BEGIN = "<!-- TOKEN-SAVER:BEGIN -->"
END = "<!-- TOKEN-SAVER:END -->"
SHIM = """<!-- TOKEN-SAVER:BEGIN -->
## Token Saver

Apply the token-saver fast path to every task: load only relevant context, preserve constraints, evidence, decisions, and accepted artifacts, avoid repeated output, and stop when complete. Invoke the full `token-saver` skill for large, iterative, retrieval-heavy, strict-format, or retry-prone work.
<!-- TOKEN-SAVER:END -->"""


def upsert_block(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if BEGIN in text and END in text:
        start = text.index(BEGIN)
        end = text.index(END, start) + len(END)
        text = text[:start].rstrip() + "\n\n" + SHIM + "\n" + text[end:].lstrip()
    else:
        text = text.rstrip() + ("\n\n" if text.strip() else "") + SHIM + "\n"
    path.write_text(text, encoding="utf-8")


def destinations(platform: str, scope: str, project: Path):
    home = Path.home()
    result = []
    if platform in {"claude", "all"}:
        skill = (home / ".claude/skills/token-saver") if scope == "global" else (project / ".claude/skills/token-saver")
        instructions = (home / ".claude/CLAUDE.md") if scope == "global" else (project / "CLAUDE.md")
        result.append(("claude", skill, instructions))
    if platform in {"codex", "all"}:
        skill = (home / ".codex/skills/token-saver") if scope == "global" else (project / ".codex/skills/token-saver")
        instructions = (home / ".codex/AGENTS.md") if scope == "global" else (project / "AGENTS.md")
        result.append(("codex", skill, instructions))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["claude", "codex", "all"], default="all")
    parser.add_argument("--scope", choices=["global", "project"], default="global")
    parser.add_argument("--project", default=".")
    parser.add_argument("--always-on", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    project = Path(args.project).resolve()
    for name, target, instructions in destinations(args.platform, args.scope, project):
        if target.exists():
            if not args.force:
                raise SystemExit(f"{target} exists; rerun with --force to replace it.")
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SKILL_SOURCE, target)
        if args.always_on:
            upsert_block(instructions)
        print(f"Installed {name} skill: {target}")
        if args.always_on:
            print(f"Updated always-on instructions: {instructions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
