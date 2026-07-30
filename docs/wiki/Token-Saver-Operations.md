# Token Saver operations

Token Saver is explicitly invoked when a task benefits from bounded retrieval, safe compaction, durable handoffs, retry-loop control, advisory routing, or exact output validation.

## Requirements

- Python 3.11 or newer
- Git when repository `.gitignore` enforcement is required
- no required third-party runtime dependencies

## Install

Install the package into an isolated environment, expose the `token-saver` command on your path, and verify it before use:

```bash
python3 -m venv ~/.local/share/token-saver/venv
~/.local/share/token-saver/venv/bin/python -m pip install --no-deps .
ln -s ~/.local/share/token-saver/venv/bin/token-saver ~/.local/bin/token-saver
token-saver doctor
```

Install the Agent Skill through the repository's safe symlink installer:

```bash
python3 scripts/install.py --platform codex --scope global
```

## Core commands

```bash
token-saver retrieve --root . --query "specific search terms"
token-saver compact --input context.json --output handoff.json --save-handoff
token-saver handoff show
token-saver artifact add plan.md --label "plan"
token-saver retry-check --operation "command" --error "failure" --input-hash "hash" --strategy "strategy"
token-saver route --request "task description"
token-saver validate-output answer.json --json
```

## Operating sequence

1. Define the goal, constraints, evidence requirements, acceptance tests, and output contract.
2. Recall durable context from [AgentPrizm](AgentPrizm) when it is available.
3. Verify mutable facts against the repository or live system.
4. Retrieve narrow passages before opening large files.
5. Compact only when it preserves every protected requirement.
6. Carry accepted artifacts and decisions into the next handoff.
7. Stop identical retries and change the evidence, input, hypothesis, strategy, or scope.
8. Validate the result before reporting completion.
9. Save durable, non-obvious outcomes to AgentPrizm; leave routine edits and recoverable facts in the repository.

## Safety properties

- Retrieval is bounded, ignore-aware, secret-aware, and symlink-safe.
- Discarded raw chunks are not serialized into compact output.
- Exact content is referenced only when its source is verified as reopenable.
- Protected content over budget returns an explicit infeasible status.
- Repository state uses concurrency-safe SQLite transactions and repository/branch scoping.

For complete commands and examples, see the [README](https://github.com/eavakyan/token-saver-skill#readme).
