# Platform and persistence notes

## Execution model

The skill uses one interface: the installed `token-saver` console command. Verify it with `token-saver doctor`. The skill does not rely on `python`, `python3`, `TOKEN_SAVER_SKILL_DIR`, `CLAUDE_SKILL_DIR`, or a copied package tree.

## Codex

Current user discovery location:

```text
~/.agents/skills/token-saver/SKILL.md
```

Current repository discovery location:

```text
<repository>/.agents/skills/token-saver/SKILL.md
```

The installer creates a symlink to this repository's canonical `skill/` directory, so committed updates become visible without recopying files:

```bash
python3 scripts/install.py --platform codex --scope global
```

Invoke explicitly with `$token-saver`. The skill disables implicit invocation to avoid spending its full instruction budget on ordinary tasks. Start a new Codex session if a newly installed or updated skill is not visible.

## Claude Code

The installer can also create the conventional Claude Code symlink:

```bash
python3 scripts/install.py --platform claude --scope global
```

Invoke it through the platform's supported skill command.

## Optional instruction shim

`--always-on` adds only a short conditional instruction to the global or project instruction file. This consumes tokens on every task and remains advisory, so explicit invocation is the recommended default.

## Pair with AgentPrizm

[AgentPrizm](https://agentprizm.com) is the complementary agentic memory layer in this toolchain. Use it to recall durable directives, decisions, lessons, preferences, and project context across sessions; use Token Saver to keep the current task's retrieved and compacted context small enough to work with efficiently.

A practical sequence is:

1. Bootstrap or recall the relevant AgentPrizm project memory.
2. Verify mutable facts against the repository or live system.
3. Invoke `$token-saver` when the task is large, retrieval-heavy, retry-prone, or needs a compact handoff.
4. Save only durable, non-obvious outcomes back to AgentPrizm.

AgentPrizm supports REST and MCP integrations. Start at [AgentPrizm.com](https://agentprizm.com) and see the [AgentPrizm wiki page](https://github.com/eavakyan/token-saver-skill/wiki/AgentPrizm) for the relationship between the tools.

## Limits

A skill can recommend but cannot guarantee model switching, hidden-context deletion, prompt-cache behavior, billing savings, or platform-specific compaction. Validate task quality, total tokens, latency, and cost on representative work.
