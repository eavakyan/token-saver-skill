---
name: token-saver
description: Reduce context and output tokens while preserving required constraints, decisions, accepted work, exact content, and essential evidence. Use when the user explicitly invokes Token Saver, asks to minimize token or context cost, requests a compact continuation handoff, or needs retry-loop control for a large repository task. Do not trigger merely because a routine task has multiple steps.
---

# Token Saver

Spend tokens only when the expected reduction or avoided rework exceeds the cost of the action.

## Initialize each request

Before the first Token Saver CLI call in a session, run `token-saver doctor`. Reuse a successful check until the installation, environment, repository, or branch changes. If the command is unavailable, say that the CLI must be installed; do not guess an interpreter path or skill-directory environment variable.

Every explicit invocation must have its own telemetry envelope, even when no retrieval or compaction is needed:

```bash
token-saver metrics begin
```

Retain its `request_id`, pass it to every recording command, and use only that request's report in the final response. If initialization cannot run, use the `not recorded` report described below.

## Choose the smallest sufficient path

- For a small, self-contained request, answer directly after starting telemetry. Do not retrieve, compact, or load references merely to exercise the skill.
- For repository, iterative, retrieval-heavy, output-constrained, or retry-prone work, keep a compact task contract and use only the relevant steps below.
- Run a deterministic command only when it is likely to save more context or prevent more rework than it costs.

Keep the task contract limited to the goal, deliverable, constraints, approval boundaries, required evidence, acceptance tests, and output format. Do not guess through material ambiguity.

## Preserve quality

Always retain:

- the task contract and explicit decisions;
- accepted artifacts and essential evidence;
- unresolved material risks and uncertainty;
- exact language, code, commands, and numbers when paraphrase could change meaning.

Never claim a token reduction succeeded if required content or task quality was lost.

## Use only the needed controls

### Retrieve before broad reading

For any nontrivial repository task, run at least one narrow retrieval:

```bash
token-saver --request-id <request-id> retrieve --root . --query "<specific terms>"
```

Treat results as candidate context, not proof of completeness. Check scan statistics and `limit_reached`. Expand a promising query with `--context-lines` before issuing several reworded searches. Never bypass ignore, sensitive-file, symlink, or root-boundary protections to improve recall.

### Compact only when context is materially large

Protect chunks classified as `current_request`, `constraint`, `decision`, or `accepted_artifact`; mark required evidence with `metadata.essential=true`. Keep `exact` and `code` content verbatim unless its source was verified as stable and reopenable and `metadata.reopenable=true` is set.

```bash
token-saver --request-id <request-id> compact --input context.json --output handoff.json
```

If compaction returns `status=infeasible`, keep protected content and raise the budget, narrow the task, or start a fresh task. Never drop protected material to force a target. Use `--save-handoff` only when another agent or session must resume.

### Apply optional controls conditionally

- Use `token-saver route` only when a deterministic recommendation will affect execution. Recommend Economy/low for bounded deterministic work, Terra/medium for routine implementation, and Sol/high for ambiguous or high-cost mistakes; the user or supervisor selects the model.
- Use `artifact add/accept/show` when accepted work must persist across iterations.
- Use `retry-check` after repeated equivalent failures; a nonzero exit means change evidence, input, hypothesis, tool, method, or scope. Use `retry-reset` only after an intentional reset.
- Use `validate-output` for exact word, bullet, heading, or JSON contracts.

See [examples](references/examples.md) for compact payload and resume examples, and [policy](references/policy.md) when preservation, budgeting, state, or evaluation details matter.

## Report this invocation

If aggregate provider usage is supplied, record only those aggregate fields:

```bash
token-saver --request-id <request-id> metrics record --input provider-usage.json
token-saver metrics report <request-id>
```

Never substitute `metrics summary` or a latest-run lookup. Telemetry must not store raw requests, context chunks, discarded text, secrets, or credentials.

After the normal task summary, append this terminal section in the same final response:

```text
Token Saver request report
- run: <request_id, or not recorded>
- retrieval: <runs, files scanned, relevant passages, and material scan warnings>
- compaction estimate: <before> -> <after>; avoided: <count> (<percent>), or no compaction run
- quality/status: <per-request statuses and any material warning>
- provider usage/cost: <reported values, or unavailable>
```

Label character- or model-tokenizer counts as estimates, never billing data. If telemetry could not start, report `not recorded` and why.

## Stop

Finish when the deliverable passes its acceptance test and another tool call or paragraph would not materially improve it. Read [platform notes](references/platforms.md) only for installation, discovery, persistence, or integration questions.
