# Token Saver

Token Saver is an explicit-invocation Agent Skill and deterministic Python toolkit for reducing context and output tokens without dropping task-critical information.

It provides:

- bounded, ignore-aware source retrieval;
- safe context handoffs that preserve constraints, decisions, exact content, and essential evidence;
- concurrency-safe artifact, retry, and handoff state;
- append-only local run telemetry and request-level metrics reports;
- output-contract validation;
- advisory model routing;
- representative quality-and-reduction regression fixtures.

It does not intercept model requests, force model changes, erase hidden platform context, or guarantee billing savings.

## Part of the AgentPrizm toolchain

Token Saver is one extension of a broader set of tools we are developing to help AI agents build and operate businesses with better continuity, efficiency, and operational discipline.

Token Saver keeps the active working context focused. [AgentPrizm](https://agentprizm.com) provides the complementary agentic memory layer: durable, governed recall across agents and sessions through REST and MCP, with confidence and validity metadata, audit receipts, and explicit memory lifecycle controls.

Try AgentPrizm at [AgentPrizm.com](https://agentprizm.com), then use the two tools together:

1. Recall durable project directives, decisions, lessons, and relevant facts from AgentPrizm.
2. Use Token Saver to retrieve and compact the smallest sufficient working context for the current task.
3. Verify mutable facts against the repository or live system before acting.
4. Store only durable outcomes that will save meaningful future work; do not store secrets or routine edits.

See the [project wiki](https://github.com/eavakyan/token-saver-skill/wiki) for an introduction to the project, its operation, Gene Avakyan, and AgentPrizm.

## Requirements

- Python 3.11 or newer
- Git for full `.gitignore` enforcement in repositories
- No required third-party runtime dependencies
- Optional `tiktoken` support for callers that use the tokenizer module directly

## Install the CLI

For an isolated, persistent macOS/Linux install whose launcher is on the standard user PATH:

```bash
cd /Users/<username>/<development-directory>/general_system_work/token-saver
python3 -m venv ~/.local/share/token-saver/venv
~/.local/share/token-saver/venv/bin/python -m pip install --no-deps .
ln -s ~/.local/share/token-saver/venv/bin/token-saver ~/.local/bin/token-saver
token-saver doctor
```

If those paths already exist, verify their targets before replacing anything. To update an existing installation after pulling or committing changes:

```bash
~/.local/share/token-saver/venv/bin/python -m pip install --force-reinstall --no-deps --no-cache-dir .
```

A normal non-editable install into another managed environment also works with `python3 -m pip install .`.

For development:

```bash
python3 -m pip install -e .
```

The skill itself invokes only the `token-saver` console command. It does not depend on interpreter aliases or undocumented skill-directory environment variables.

## Install the Codex skill persistently

After `token-saver doctor` succeeds:

```bash
cd /Users/<username>/<development-directory>/general_system_work/token-saver
python3 scripts/install.py --platform codex --scope global
```

This creates:

```text
~/.agents/skills/token-saver -> /Users/<username>/<development-directory>/general_system_work/token-saver/skill
```

The symlink keeps the repository as the canonical source. The installer is idempotent when the correct link already exists. With `--force`, an existing target is moved to a timestamped backup rather than deleted.

Start a new Codex session if the skill does not appear immediately. Invoke it explicitly:

```text
$token-saver Inspect this repository and fix the failing tests with the smallest sufficient context.
```

Implicit invocation is disabled so ordinary tasks do not pay to load the full workflow. `--always-on` is available but not recommended by default because even its small instruction shim consumes context on every task.

Project-scoped discovery uses `.agents/skills/token-saver`:

```bash
python3 scripts/install.py --platform codex --scope project --project /path/to/repository
```

Safe uninstall removes only a symlink and refuses to delete a copied directory:

```bash
python3 scripts/uninstall.py --platform codex --scope global
```

## Common workflows

### Retrieve narrow passages

```bash
token-saver retrieve \
  --root . \
  --query "OAuth refresh token validation" \
  --top-files 8 \
  --passages-per-file 3 \
  --context-lines 6
```

Retrieval skips symlinks, Git-ignored files, configured sensitive names, recognized secret material, binary files, and common generated directories. It reports file and byte limits so truncated scans are visible.
Increase `--context-lines` around a promising hit before spending more calls on reworded queries.

### Build a safe compact handoff

Input:

```json
{
  "request": "Fix the refresh-token race condition",
  "chunks": [
    {"id": "requirements", "kind": "constraint", "text": "Do not change the public API."},
    {"id": "decision", "kind": "decision", "text": "Use a per-user lock."},
    {"id": "proof", "kind": "evidence", "text": "The concurrency test reproduces the race.", "metadata": {"essential": true}},
    {"id": "implementation", "kind": "code", "text": "def refresh(): ...", "source": "app/auth.py:40", "metadata": {"reopenable": true}},
    {"id": "old-draft", "kind": "draft", "text": "Discarded implementation...", "metadata": {"superseded": true}}
  ]
}
```

Run:

```bash
token-saver compact --input context.json --output handoff.json --save-handoff
```

Compaction records derived run metrics by default. Add `--no-record` when local telemetry is not appropriate. The output includes a run ID, estimated input tokens before/after, avoided tokens, savings percentage, actions, tokenizer used, status, and warnings. No raw request or context text is written to telemetry.

Review the local append-only history:

```bash
token-saver metrics summary
token-saver metrics show <run-id>
token-saver metrics export --output token-saver-runs.jsonl
```

### Per-request reports, including parallel jobs

Start every explicit Token Saver invocation with its own request ID, attach it to every recording command, and render the final report from that ID only. This keeps concurrent jobs on a shared branch from mixing or omitting statistics:

```bash
token-saver metrics begin
# Read request_id from the JSON result.
token-saver --request-id <request-id> retrieve --root . --query "OAuth refresh token validation"
token-saver --request-id <request-id> compact --input context.json --output handoff.json
token-saver metrics report <request-id>
```

`metrics report` includes exact retrieval scan and passage counts, per-request statuses, compaction estimates when compaction ran, and aggregate provider usage when supplied. Do not use `metrics summary` or a latest-run heuristic for a final request report: both are scope-wide and therefore ambiguous when jobs run in parallel. For a small direct task with no retrieval or compaction, report the zero operation counts rather than claiming its statistics are unavailable.

Provider/API usage is not visible to the skill automatically. If the platform supplies aggregate usage metadata, it can be recorded separately without storing prompt content:

```bash
token-saver --request-id <request-id> metrics record --input provider-usage.json
```

When `$token-saver` is invoked, the agent should append a `Token Saver request report` after its normal task summary. Estimated counts must remain labeled as estimates; provider usage and billing must be labeled unavailable unless supplied by the platform or caller.

The output contains selected handoff content and compact decision metadata, never the original raw body of discarded chunks. Exact content becomes a reference only when `metadata.reopenable=true` confirms that its source was verified. `status=infeasible` and exit code `4` mean protected material alone exceeds the budget; narrow the task or raise the budget instead of dropping required facts.

### Durable handoffs and artifacts

```bash
token-saver handoff show
token-saver artifact add plan.md --label "authentication plan"
token-saver artifact accept <artifact-id>
token-saver artifact show --accepted
```

State defaults to `<git-root>/.token-saver/state.sqlite3`, permissions are restricted locally, and records are scoped by repository and branch. SQLite transactions prevent concurrent agents from losing artifact, retry, or handoff updates.

### Retry control

```bash
token-saver retry-check \
  --operation "pytest tests/test_auth.py" \
  --error "same assertion failure" \
  --input-hash "<diff hash>" \
  --strategy "lock-v1"
```

Exit code `3` means stop or change strategy. Counters expire after the configured TTL and can be cleared with `token-saver retry-reset`.

### Advisory model routing

```bash
token-saver route --request "Review the production authorization migration" --high-stakes
```

The policy recommends:

- Terra with medium reasoning for routine coding and tests;
- Sol with high reasoning for architecture, security, ambiguity, deep cross-file work, or costly failure;
- an economy model with low reasoning only for bounded deterministic transformations.

The result is advisory. The user, parent agent, or execution platform controls the actual model.

### Output validation

```bash
token-saver validate-output answer.txt --exact-words 50
token-saver validate-output answer.txt --exact-bullets 5
token-saver validate-output answer.json --json
```

## Configuration

The packaged default policy is `token_saver/data/default.toml`. Override it with:

```bash
export TOKEN_SAVER_CONFIG=/path/to/custom.toml
```

A specified but missing override fails closed. `TOKEN_SAVER_MODE`, `TOKEN_SAVER_STATE_DIR`, and `TOKEN_SAVER_SCOPE` can override mode and state placement or scoping.

## Validate the project

```bash
python3 -m unittest discover -s tests -v
python3 scripts/benchmark.py
python3 /path/to/skill-creator/scripts/quick_validate.py skill
```

The test suite includes a clean wheel install, installed CLI execution, Codex symlink installation, raw-context leak prevention, preservation and infeasible-budget cases, retrieval boundaries and ignore rules, concurrency checks, and routing safeguards.

The benchmark uses representative regression fixtures and fails when required chunks disappear, discarded raw markers leak, or expected budget status changes. Its token counts remain estimates, not billing measurements.

## Repository layout

```text
skill/                         Canonical Agent Skill
token_saver/                   Python package
token_saver/data/default.toml  Packaged policy defaults
scripts/install.py             Safe symlink installer
scripts/uninstall.py           Symlink-only uninstaller
scripts/benchmark.py           Quality-and-reduction regression runner
tests/                         Unit and integration tests
examples/evaluation_corpus.json
```

## Remaining limitations

- Character-based token estimates vary by language, code density, and model tokenizer.
- Secret detection is defense in depth, not a substitute for repository access controls and human review.
- Bounded lexical retrieval can miss semantically related material; broaden the query or inspect dependencies when evidence is incomplete.
- A skill can influence agent behavior but cannot guarantee platform model selection, internal context management, caching, or spend.

## License

MIT
