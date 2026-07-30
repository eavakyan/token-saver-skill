---
name: token-saver
description: Reduce context and output token use without dropping decision-critical facts, evidence, constraints, or accepted work. Use when the user says "use the token saver skill for this job", asks to save tokens or cost, works with a large repository or many files, continues a long iterative task, requests strict output limits, or risks repeated tool/retry loops. Also apply automatically to retrieval-heavy, multi-step, or long-context work.
---

# Token Saver

Apply the smallest-context workflow that can still satisfy the task.

## Non-negotiable quality rule

Treat token reduction as an optimization under a quality constraint, not as the primary objective. Preserve:

- the current request and success criteria;
- hard constraints and approval boundaries;
- accepted artifacts and explicit decisions;
- evidence needed to support the answer;
- unresolved risks, contradictions, and material uncertainty;
- exact output requirements.

Remove or compress material only when its loss cannot reasonably change the result.

## Fast path

For a small, self-contained request:

1. Answer directly.
2. Do not load references, files, tools, or history that are unnecessary.
3. Omit restatement, generic background, repeated conclusions, and unrequested process narration.
4. Match the requested length and format.
5. Stop when the task is complete.

Do not run bundled scripts merely to optimize a trivial request; script overhead must earn its place.

## Full workflow

For large, iterative, file-heavy, or tool-heavy work, execute these stages.

### 1. Normalize the request

Create a compact internal task contract containing only:

- goal;
- deliverable;
- constraints;
- required evidence;
- acceptance test;
- output contract.

Resolve obvious redundancy without changing meaning. Do not replace a materially ambiguous request with a guessed interpretation.

### 2. Route by task difficulty

Recommend the smallest model tier likely to pass:

- **economy**: extraction, formatting, deterministic edits, simple lookup, bounded transformations;
- **standard**: normal coding, synthesis, debugging with a clear failure, moderate analysis;
- **powerful**: ambiguous architecture, deep cross-file reasoning, high-stakes review, hard debugging, or tasks where failure is expensive.

A recommendation is advisory. Do not downgrade when the task's risk, ambiguity, or evaluation requires stronger reasoning.

Use `python "${TOKEN_SAVER_SKILL_DIR:-${CLAUDE_SKILL_DIR:-.}}/scripts/token_saver.py" route --request "..."` when a deterministic score is useful.

### 3. Search before opening

Before reading large files:

1. List or search filenames and symbols.
2. Rank likely sources using request terms.
3. Read narrow passages around matches.
4. Expand only when the passage is insufficient or dependencies require it.
5. Prefer clean text or Markdown over raw layout-heavy representations.
6. Never paste an entire large file into the conversation when paths, line ranges, or extracted passages suffice.

For local repositories, use the bundled retrieval command:

```bash
python "${TOKEN_SAVER_SKILL_DIR:-${CLAUDE_SKILL_DIR:-.}}/scripts/token_saver.py" retrieve \
  --root . --query "<compact search query>"
```

Treat its output as candidate context, not proof of completeness. Expand retrieval when the answer requires broader evidence.

### 4. Apply context ROI

Classify every candidate chunk:

- **keep**: required to decide, act, verify, or explain;
- **compress**: relevant but verbose;
- **reference**: stable material that can remain as a path, identifier, hash, or line range;
- **discard**: duplicate, stale, rejected, superseded, low-value, or unrelated.

Prefer this priority order:

1. current request and constraints;
2. accepted artifact and decisions;
3. required evidence and source passages;
4. compact summaries of relevant tool results;
5. unresolved critiques;
6. drafts and raw tool output;
7. rejected sources and superseded reasoning.

Deduplicate stable instructions and sources by fingerprint. Keep one canonical copy and refer to it thereafter.

When context approaches the configured budget:

- warning threshold: stop adding speculative context;
- compaction threshold: replace verbose chunks with compact summaries or references;
- fresh-task threshold: create a clean continuation containing only the task contract, accepted artifact, decisions, open issues, and essential evidence.

Do not claim to erase hidden platform context. Instead produce the smallest replacement context and continue from a fresh task/session when the platform permits.

### 5. Carry forward artifacts, not debris

At a meaningful checkpoint, retain:

- the latest user-accepted artifact;
- explicit decisions and constraints;
- open issues and next action;
- minimal provenance needed to verify the artifact.

Do not carry forward:

- rejected drafts;
- superseded plans;
- repeated criticism already incorporated;
- raw chain-of-thought or hidden reasoning;
- full tool dumps after their relevant facts are extracted;
- sources rejected as irrelevant or unreliable.

If user acceptance is not explicit, label the artifact as a candidate rather than silently promoting it.

Use the artifact CLI for persistent local state when useful:

```bash
token-saver artifact add <file> --label "<label>"
token-saver artifact accept <artifact-id>
```

### 6. Prefer deterministic work

Run exact operations as code when code is shorter, reproducible, and verifiable: filtering, counting, diffing, schema validation, formatting, deduplication, extraction, tests, and transformations.

Do not replace semantic judgment with brittle code. Use the model for interpretation, prioritization, ambiguity, and synthesis.

Reduce tool exposure when the platform permits: use only tools relevant to the current stage. Summarize tool results immediately after extracting the required facts.

### 7. Enforce the output contract

Before responding, validate:

- exact word count when requested;
- exact bullet/item count when requested;
- JSON parseability and schema when requested;
- required headings or fields;
- maximum length;
- absence of extra prose when raw output is required.

Use:

```bash
token-saver validate-output <file> --exact-words 50
token-saver validate-output <file> --exact-bullets 5
token-saver validate-output <file> --json
```

Preserve required facts, caveats, evidence, and next actions. Trim introductions, repetition, generic reassurance, process narration, and optional background first.

### 8. Stop retry loops

Fingerprint each failed attempt from:

- operation;
- normalized error;
- relevant input or diff hash;
- strategy identifier.

Retry a transient failure only within the configured limit. Stop when the same signature repeats without a material change.

Before another attempt, require at least one of:

- new evidence;
- changed input;
- changed hypothesis;
- changed tool or method;
- narrower scope;
- explicit user direction.

Do not rerun an unchanged failing command while carrying forward the complete prior transcript.

### 9. Report metrics only when useful

For substantial work, append a compact metric line only when the user requested metrics or when it helps tune the workflow:

`Token Saver: ~N input tokens avoided; K chunks kept, C compressed, D discarded; mode=M.`

Mark estimates as approximate. Do not add a metrics report to tiny answers or strict raw-output requests.

## Modes

Read `TOKEN_SAVER_MODE`; default to `balanced`.

- **quality-first**: preserve more context and evidence.
- **balanced**: remove clear waste while preserving strong support.
- **extreme**: aggressively compress routine work; escalate when quality checks fail.

Mode never overrides explicit user requirements or safety constraints.

## References

Read only when needed:

- [references/policy.md](references/policy.md) for scoring, compaction, quality gates, and artifact rules.
- [references/platforms.md](references/platforms.md) for Claude Code and Codex installation and always-on behavior.
- [references/examples.md](references/examples.md) for worked context decisions and output contracts.

## Completion gate

Before finishing, verify:

1. The answer or change satisfies the task.
2. Required evidence and caveats remain.
3. No stale draft or duplicate source is being carried forward.
4. Output constraints pass.
5. Another tool call or paragraph would materially improve the result.

If item 5 is false, stop.
