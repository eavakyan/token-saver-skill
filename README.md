# Token Saver

A cross-platform Agent Skill and deterministic Python toolkit for reducing context and output tokens without blindly sacrificing answer quality.

It is designed for:

- Claude Code
- OpenAI Codex
- Any agent that can read an Agent Skills-compatible `SKILL.md`
- Manual use from a terminal or CI pipeline

The project uses one canonical skill. Platform installers copy the same skill into each platform's discovery directory.

## What it does

Token Saver applies six controls:

1. **Retrieve before reading** — rank files and extract only relevant passages.
2. **Context ROI** — keep, compress, reference, or discard each context chunk.
3. **Artifact carry-forward** — preserve accepted outputs, not abandoned drafts and critiques.
4. **Output guards** — validate exact word, bullet, and JSON constraints.
5. **Retry-loop control** — stop repeated failures with the same inputs and error.
6. **Model routing advice** — recommend an economy, standard, or powerful model tier based on task complexity.

The skill does not alter a vendor's billing system or secretly intercept requests. It changes agent behavior and provides scripts the agent can run to deterministically reduce context.

## Expected savings

Savings depend on workload. The included benchmark measures *estimated context reduction*, not vendor billing. In long sessions with repeated files, stale drafts, and verbose tool output, substantial reductions are possible. Quality should be tested on your own representative tasks; fewer tokens are not a win if required evidence disappears.

## Requirements

- Python 3.11+
- No required third-party dependencies
- Optional: `tiktoken` for model-specific token estimates; the default estimator uses a conservative character heuristic

## Install the CLI

```bash
cd token-saver
python -m pip install -e .
```

Verify:

```bash
token-saver doctor
python -m unittest discover -s tests -v
```

## Install the skill

### Global, both Claude Code and Codex

```bash
python scripts/install.py --platform all --scope global
```

### Global and automatically applied to every request

```bash
python scripts/install.py --platform all --scope global --always-on
```

This installs:

- Claude Code skill: `~/.claude/skills/token-saver/`
- Codex skill: `~/.codex/skills/token-saver/`

The `--always-on` flag also adds a very small marked instruction block to:

- Claude Code: `~/.claude/CLAUDE.md`
- Codex: `~/.codex/AGENTS.md`

The shim tells the agent to apply the lightweight policy to every task while loading the full skill only for tasks that benefit from it. This is the best practical global mode: skill discovery is global, and the always-on shim makes invocation much less dependent on model judgment.

### Project-only install

Run from the project root:

```bash
python scripts/install.py --platform all --scope project --always-on
```

This writes to `.claude/skills/token-saver/`, `.codex/skills/token-saver/`, `CLAUDE.md`, and `AGENTS.md`.

## Invoke it

Claude Code:

```text
/token-saver Refactor the authentication module and keep the response under 300 words.
```

Codex or natural-language invocation:

```text
Use the token saver skill for this job: inspect the repository and fix the failing tests.
```

The skill description also permits automatic invocation for large-context, multi-step, retrieval-heavy, or iterative work.

## Modes

The default is `balanced`.

- `quality-first`: preserve more evidence and use larger context budgets.
- `balanced`: remove obvious waste while preserving decision-critical context.
- `extreme`: aggressively compress and prefer deterministic scripts; best for routine or high-volume work.

Set a default:

```bash
export TOKEN_SAVER_MODE=balanced
```

Or pass `--mode` to CLI commands.

## Common CLI workflows

### Rank files and extract passages

```bash
token-saver retrieve \
  --root . \
  --query "OAuth refresh token validation" \
  --top-files 8 \
  --passages-per-file 3
```

### Build a compact context bundle

Prepare a JSON input containing context chunks:

```json
{
  "request": "Fix the refresh-token race condition",
  "chunks": [
    {"id": "requirements", "kind": "constraint", "text": "Do not change the public API."},
    {"id": "accepted-plan", "kind": "accepted_artifact", "text": "Use a per-user lock."},
    {"id": "old-draft", "kind": "draft", "text": "A discarded first implementation..."}
  ]
}
```

Then run:

```bash
token-saver compact --input context.json --output compacted.json
```

### Validate an output contract

```bash
token-saver validate-output answer.txt --exact-words 50
token-saver validate-output answer.txt --exact-bullets 5
token-saver validate-output answer.json --json
```

### Promote the accepted artifact

```bash
token-saver artifact add draft.md --label "authentication plan"
token-saver artifact accept <artifact-id>
token-saver artifact show --accepted
```

Only the accepted artifact is selected for future carry-forward.

### Retry guard

```bash
token-saver retry-check \
  --operation "pytest tests/test_auth.py" \
  --error "same assertion failure" \
  --max-retries 2
```

A non-zero exit status means the loop should stop or materially change strategy.

### Benchmark

```bash
python scripts/benchmark.py
```

## Configuration

Default policies live in `config/default.toml`. Override with:

```bash
export TOKEN_SAVER_CONFIG=/path/to/custom.toml
```

The loader merges your file over the defaults.

## Global versus per-request use

You do **not** need to type the activation phrase on every request when installed globally with `--always-on`.

There are three practical levels:

1. **Manual:** invoke `/token-saver` or say “use the token saver skill for this job.”
2. **Global discoverable:** install under the global skills directory; the agent loads it when the description matches.
3. **Global always-on:** add the tiny global shim. The fast-path rules apply to every request; the full skill loads only for work where retrieval, compaction, artifacts, output validation, routing, or retry control can help.

The third option gives the most consistent behavior while keeping permanent prompt overhead small.

## Security and privacy

- No API keys are required.
- The toolkit does not upload files.
- State is local under `.token-saver/` by default.
- Retrieval skips common secret files, VCS directories, build outputs, and binary files.
- Review extracted context before sending it to any external model.

## Limits

- A skill cannot guarantee that a hosted UI switches models; it can recommend a tier.
- Token estimates are approximate unless a tokenizer matching the target model is installed.
- Automatic context deletion is platform-dependent. The skill instead tells the agent what not to carry forward and produces compact replacement bundles.
- PDF conversion is intentionally not bundled. Agents should use their platform's PDF tools or a trusted local extractor and pass only relevant text into the compactor.

## Repository layout

```text
skill/                    Canonical cross-platform Agent Skill
token_saver/              Deterministic Python toolkit
scripts/install.py        Claude Code and Codex installer
scripts/uninstall.py      Safe uninstaller
scripts/benchmark.py      Synthetic token-reduction benchmark
config/default.toml       Policy modes and thresholds
tests/                    Unit tests
examples/                 Example inputs
```

## License

MIT
