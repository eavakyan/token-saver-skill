# Token Saver policy reference

## Preservation

Always retain the current task contract, approval boundaries, accepted artifacts, explicit decisions, essential evidence, unresolved material risks, and exact content whose meaning could change under summarization.

Exact or code content may become a source reference only when the caller has verified the source is stable and reopenable and sets `metadata.reopenable=true`. A source string alone is insufficient. Otherwise keep the content verbatim. Never summarize exact legal text, security-sensitive commands, numerical datasets, or code when exactness is required.

## Context decisions

Score non-protected material by kind, relevance, freshness, authority, uniqueness, and dependency. Then choose:

- `keep` when compact and needed now;
- `compress` when relevant but verbose and safe to paraphrase;
- `reference` when a stable source can be reopened cheaply;
- `discard` when duplicate, rejected, superseded, unrelated, or low value.

If protected content alone exceeds the configured budget, return `status=infeasible`. Do not falsify compliance by dropping it.

## Safe handoff

A handoff should answer:

1. What is the goal and acceptance test?
2. What is constrained or forbidden?
3. Which decisions and artifacts are current?
4. What evidence supports the next action?
5. What remains unresolved?

Normal compact output contains the selected handoff content plus fingerprints and decision metadata. It must not serialize original discarded chunks.

## State

State defaults to `<git-root>/.token-saver/state.sqlite3` and a repository-plus-branch scope. SQLite transactions protect concurrent artifact acceptance, retry counters, and handoff replacement. Use an explicit shared `--state-scope` only when agents intentionally coordinate.

Token Saver also keeps append-only run telemetry for retrieval and compaction. Telemetry is limited to derived metrics, fingerprints, scan statistics, warnings, and explicitly supplied aggregate provider usage. It must never contain raw requests, context chunks, discarded text, secrets, or credentials. Use `--no-record` when local recording is inappropriate.

Retry signatures expire after the configured TTL and can be reset. A retry must change evidence, inputs, hypothesis, strategy, method, or scope after the allowed identical attempts are exhausted.

## Durable memory boundary

Token Saver state supports the current repository workflow; it is not intended to be the permanent memory of record for every agent or business process. For durable, cross-session context, pair it with the [AgentPrizm agentic memory layer](https://agentprizm.com).

Store durable directives, decisions, non-obvious lessons, milestones, and facts that would save substantial future work. Do not store secrets, credentials, routine edits, transient logs, current line numbers, or facts that are trivial to recover from the repository. Treat recalled memory as historical context and verify mutable facts before making consequential changes.

## Evaluation

Measure task success and required-fact retention before token reduction. Then compare estimated input/output tokens, files opened, retries avoided, latency, and cost. Character-based token estimates are approximate; synthetic benchmarks are regression fixtures, not billing claims.
