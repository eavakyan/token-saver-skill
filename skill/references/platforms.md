# Platform Notes

## Canonical skill

The same `skill/` directory is installed on both platforms. Keep behavior in one `SKILL.md`; keep platform differences in installers and this reference.

## Claude Code

Personal skills:

```text
~/.claude/skills/token-saver/SKILL.md
```

Project skills:

```text
<project>/.claude/skills/token-saver/SKILL.md
```

Direct invocation:

```text
/token-saver <task>
```

Automatic invocation depends on the skill description and model judgment. For consistent lightweight application, add the marked Token Saver shim to global `~/.claude/CLAUDE.md` or project `CLAUDE.md`.

Do not paste the entire skill into `CLAUDE.md`; that would permanently consume context. The shim should remain tiny and point to the skill.

## Codex

Personal skills:

```text
~/.codex/skills/token-saver/SKILL.md
```

Project skills:

```text
<project>/.codex/skills/token-saver/SKILL.md
```

Invoke naturally or through the platform's skill syntax, for example:

```text
Use the token saver skill for this job: <task>
```

For consistent lightweight application, add the marked Token Saver shim to `~/.codex/AGENTS.md` or the project's root `AGENTS.md`.

Restart Codex after adding a new skill if the running version does not hot-reload skill discovery.

## Always-on shim

The installer writes this compact behavior:

```text
Apply the token-saver fast path to every task: load only relevant context, preserve constraints/evidence/accepted artifacts, avoid repeated output, and stop when complete. Invoke the full token-saver skill for large, iterative, retrieval-heavy, strict-format, or retry-prone work.
```

This is intentionally small. Global instructions are loaded frequently; placing the full policy there would undermine the goal.

## Platform limitations

A skill can influence but may not control:

- which model a hosted UI selects;
- internal context compaction;
- hidden reasoning retention;
- prompt-cache billing;
- tool-definition injection.

Use the skill to produce compact source passages, accepted-artifact records, and fresh-task handoffs that the platform can consume.
