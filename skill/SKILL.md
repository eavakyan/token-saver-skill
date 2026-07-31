---
name: token-saver
description: Reduce context and output tokens while preserving required constraints, decisions, accepted work, exact content, and essential evidence. Use when the user explicitly invokes Token Saver, asks to minimize token or context cost, requests a compact continuation handoff, or needs retry-loop control for a large repository task. Do not trigger merely because a routine task has multiple steps.
---

# Token Saver

Minimize tokens only when the result still satisfies the task.

## Quality boundary

Preserve:

- the current goal, deliverable, constraints, and acceptance test;
- explicit decisions and accepted artifacts;
- essential evidence, unresolved risks, and material uncertainty;
- exact language, code, commands, and numerical data when paraphrase could alter meaning;
- the requested output format.

Never report token reduction as a success when required content or task quality is lost.

## Choose the path

For a small self-contained request, answer directly. Avoid loading files, history, references, or scripts that do not change the result.

For a large, iterative, retrieval-heavy, output-constrained, or retry-prone request, use the workflow below. Run deterministic commands only when their output will save more context or prevent rework than the call costs.

## Per-request telemetry

Every explicit Token Saver invocation must use its own telemetry envelope, including when the task needs no retrieval or compaction. This prevents parallel jobs on the same branch from omitting, mixing, or borrowing each other's statistics.

At the beginning, run `token-saver metrics begin` and retain its `request_id`. Pass that identifier to every recording command in this invocation:

```bash
token-saver --request-id <request-id> retrieve --root . --query "<specific search terms>"
token-saver --request-id <request-id> compact --input context.json --output handoff.json
token-saver --request-id <request-id> metrics record --input provider-usage.json
```

Before writing the final response, run `token-saver metrics report <request-id>`. Use only that output for the request report; never use a scope-wide summary or a "latest run" lookup. For a repository or other nontrivial task, run at least one narrow retrieval so the report includes scan and passage statistics. A truly small direct task may have zero retrieval and compaction runs; say so explicitly rather than calling the statistics unavailable.

## Full workflow

### 1. Form the task contract

Keep one compact record of:

- goal and deliverable;
- constraints and approval boundaries;
- required evidence;
- acceptance tests;
- output contract.

Do not resolve material ambiguity by guessing.

### 2. Advise on model routing

Recommend a model; do not claim to switch the hosted model silently.

- **Terra / medium**: routine coding, testing, synthesis, and debugging with a clear failure.
- **Sol / high**: architecture, security, ambiguous failures, deep cross-file work, or mistakes with high cost.
- **Economy / low**: bounded deterministic extraction, formatting, validation, or transformation with a clear acceptance test.

Escalate rather than downgrade when correctness, evidence, or safety is uncertain. The user or task supervisor makes the final selection.

Run this only when a deterministic recommendation helps:

```bash
token-saver route --request "<task>" --file-count <count>
```

Add `--high-stakes` for consequential security, production, legal, medical, or financial work.

### 3. Retrieve before reading

Search filenames and symbols first. Read narrow passages, then expand only when dependencies or missing evidence require it.

```bash
token-saver --request-id <request-id> retrieve --root . --query "<specific search terms>"
```

Treat retrieval output as candidate context, not proof of completeness. Inspect its scan statistics and broaden deliberately if a limit was reached. Never bypass ignored-file, sensitive-file, or root-boundary protections merely to improve recall.

When a hit is correct but its adjacent implementation is incomplete, rerun the same query with `--context-lines <larger count>` instead of issuing several reworded searches.

### 4. Compact safely

Classify context chunks as:

- `current_request`, `constraint`, `decision`, or `accepted_artifact` for protected task state;
- `evidence` with `metadata.essential=true` for evidence required by the result;
- `exact` or `code` for content that must remain exact; set `metadata.reopenable=true` only after verifying its `source` can be reopened;
- `source_passage`, `tool_result`, or `summary` for reopenable or compressible material;
- `draft`, `critique`, `rejected_source`, or `reasoning` for low-value or superseded material.

Run:

```bash
token-saver --request-id <request-id> compact --input context.json --output handoff.json
```

The normal output is a safe handoff and decision audit; it never echoes discarded raw chunks. Exact content becomes a reference only when its source is explicitly marked verified and reopenable. If `status` is `infeasible`, preserve protected content and either raise the budget, narrow the task, or start a fresh task. Never silently drop protected material to force the metric under budget.

Use `--save-handoff` when another agent or session must resume from the compact result.

### 5. Carry accepted work forward

Store candidates and explicitly accept the chosen artifact:

```bash
token-saver artifact add <file> --label "<logical label>"
token-saver artifact accept <artifact-id>
token-saver artifact show --accepted
```

Use `artifact reject` or `artifact archive` for material that should not re-enter normal context. State is scoped by repository and branch by default; use global `--state-scope <name>` when coordinating a deliberate shared scope.

For a structured continuation that is not produced by `compact`:

```bash
token-saver handoff save --input handoff.json
token-saver handoff show
```

### 6. Stop repeated failures

```bash
token-saver retry-check \
  --operation "<operation>" \
  --error "<normalized failure>" \
  --input-hash "<relevant input or diff hash>" \
  --strategy "<strategy id>"
```

A nonzero exit means stop or materially change the evidence, input, hypothesis, tool, method, or scope. Use `token-saver retry-reset` after an intentional reset. Do not use retries to bypass permissions, invalid credentials, malformed input, or deterministic failures.

### 7. Validate the output contract

Use `token-saver validate-output` for exact word counts, bullet counts, headings, or JSON parseability. Trim repetition, introductions, generic reassurance, and optional background before removing evidence or caveats.

### 8. Record and report the request

`compact` and `retrieve` append a privacy-preserving local run record by default. The record contains derived counts, actions, warnings, scan statistics, fingerprints, and optional caller-supplied provider usage; it never stores raw requests, context chunks, discarded text, secrets, or credentials. Use `--no-record` only when local telemetry is not appropriate.

Inspect or export the local history with:

```bash
token-saver metrics summary
token-saver metrics show <run-id>
token-saver metrics export --output token-saver-runs.jsonl
```

If the platform or API supplies actual usage metadata, record only the aggregate fields:

```bash
token-saver metrics record --input provider-usage.json
```

After the normal user-facing task summary, append this report as the final section of every request where Token Saver is invoked:

```text
Token Saver request report
- run: <request_id, or not recorded>
- retrieval: <runs, files scanned, relevant passages, and material scan warnings>
- compaction estimate: <before> -> <after>; avoided: <count> (<percent>), or no compaction run
- quality/status: <per-request statuses and any material warning>
- provider usage/cost: <reported values, or unavailable>
```

Delivery rule: place this report in the same final user-facing response that completes the request. It must be the terminal section of that response, after the normal summary; do not emit it only in commentary, a tool result, a local log, or a later follow-up. Include it even when no Token Saver CLI command ran, using the `not recorded` status below.

Clearly label character-based or model-tokenizer values as estimates. Never present them as provider billing data. If no Token Saver command ran, report `not recorded: no retrieval or compaction operation was needed`.

### 9. Stop

Finish when the deliverable passes its acceptance test and another tool call or paragraph would not materially improve it.

## CLI availability

Use the installed `token-saver` console command as the only execution interface. Start with `token-saver doctor`. If it is unavailable, report that the CLI must be installed; do not guess an interpreter path or a skill-directory environment variable.

## References

Read only when needed:

- [references/policy.md](references/policy.md) for preservation, budget, state, and evaluation rules.
- [references/platforms.md](references/platforms.md) for installation and persistence.
- [references/examples.md](references/examples.md) for compact input and handoff examples.
