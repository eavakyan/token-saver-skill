#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path


BEGIN = "<!-- TOKEN-SAVER:BEGIN -->"
END = "<!-- TOKEN-SAVER:END -->"


def remove_block(path: Path) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if BEGIN not in text or END not in text:
        return
    start = text.index(BEGIN)
    end = text.index(END, start) + len(END)
    updated = (text[:start].rstrip() + "\n\n" + text[end:].lstrip()).strip()
    if updated:
        temporary = path.with_name(f".{path.name}.token-saver.tmp")
        temporary.write_text(updated + "\n", encoding="utf-8")
        os.replace(temporary, path)
    else:
        path.unlink()


def targets(platform: str, scope: str, project: Path):
    home = Path.home()
    result = []
    if platform in {"claude", "all"}:
        result.append((
            home / ".claude/skills/token-saver" if scope == "global" else project / ".claude/skills/token-saver",
            home / ".claude/CLAUDE.md" if scope == "global" else project / "CLAUDE.md",
        ))
    if platform in {"codex", "all"}:
        result.append((
            home / ".agents/skills/token-saver" if scope == "global" else project / ".agents/skills/token-saver",
            home / ".codex/AGENTS.md" if scope == "global" else project / "AGENTS.md",
        ))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove Token Saver symlinks without deleting source or copied directories.")
    parser.add_argument("--platform", choices=["claude", "codex", "all"], default="codex")
    parser.add_argument("--scope", choices=["global", "project"], default="global")
    parser.add_argument("--project", default=".")
    parser.add_argument("--remove-always-on", action="store_true")
    args = parser.parse_args()

    for skill, instructions in targets(args.platform, args.scope, Path(args.project).resolve()):
        if skill.is_symlink():
            skill.unlink()
            print(f"Removed symlink {skill}")
        elif skill.exists():
            raise SystemExit(f"Refusing to delete non-symlink skill directory: {skill}")
        if args.remove_always_on:
            remove_block(instructions)
            print(f"Removed marked instructions from {instructions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
