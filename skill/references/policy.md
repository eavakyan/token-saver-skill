# Token Saver Policy Reference

## 1. Context ROI model

Score a context chunk from 0 to 1:

```text
score =
  kind_weight
  × relevance
  × freshness
  × authority
  × uniqueness
  × dependency
```

Where:

- `kind_weight` is configured by chunk type.
- `relevance` measures overlap or semantic connection to the current task.
- `freshness` falls when a chunk is superseded.
- `authority` rises for primary sources, executable tests, and explicit user decisions.
- `uniqueness` falls for duplicate or near-duplicate material.
- `dependency` rises when later work directly relies on the chunk.

Decisions:

- Keep when the score exceeds the mode threshold and the chunk is compact.
- Compress when it exceeds the threshold but is verbose.
- Reference when the source can be re-opened cheaply and exact contents are not needed now.
- Discard when below threshold, superseded, rejected, or duplicative.

Hard-preserve current requests, explicit constraints, accepted artifacts, material safety information, and evidence required by the output—even if lexical relevance appears low.

## 2. Quality gates

A compacted bundle passes only if a reviewer can answer:

1. What is being done?
2. What counts as complete?
3. What is forbidden or constrained?
4. What decisions are already settled?
5. Which artifact is current?
6. What evidence supports the next action or final claim?
7. What remains unresolved?

If any answer is missing, restore the smallest chunk that supplies it.

## 3. Summarization rules

A summary should preserve:

- entities, values, dates, identifiers, paths, and versions;
- decisions and their rationale when the rationale affects future work;
- failures and the tested conditions;
- source provenance or line ranges;
- unresolved contradictions and uncertainty;
- API contracts, schemas, and acceptance tests.

Drop:

- greetings and transitions;
- repeated explanation;
- abandoned alternatives after the rejection reason is captured;
- verbose logs after extracting the failing command, error, and relevant state;
- generic advice;
- raw reasoning traces.

Never summarize exact legal language, security-sensitive commands, numerical datasets, or code when exactness is required. Reference or extract the exact passage instead.

## 4. Artifact lifecycle

States:

- `candidate`: generated but not accepted.
- `accepted`: explicitly accepted or designated by the user.
- `superseded`: replaced by a later accepted artifact.
- `rejected`: explicitly rejected.
- `archived`: retained locally but excluded from normal carry-forward.

Only one artifact per logical label should normally be accepted. Accepting a new artifact supersedes the prior accepted artifact with the same label.

Carry-forward record:

```json
{
  "goal": "...",
  "constraints": ["..."],
  "decisions": ["..."],
  "accepted_artifact": {
    "id": "...",
    "path": "...",
    "fingerprint": "..."
  },
  "open_issues": ["..."],
  "evidence": [
    {"source": "path", "range": "L10-L24", "claim": "..."}
  ],
  "next_action": "..."
}
```

## 5. Retry policy

Retry automatically only for plausible transient failures: timeouts, rate limits, network errors, temporary locks, or flaky tests with known nondeterminism.

Do not retry unchanged:

- syntax or type errors;
- permission failures;
- invalid credentials;
- deterministic assertion failures;
- malformed requests;
- missing required input;
- rejected external actions.

After two matching failures, stop by default. Report the stable failure signature and the smallest useful diagnostic.

## 6. Model-tier rubric

Add points:

- +1 for more than 5 relevant files.
- +1 for cross-module or cross-domain synthesis.
- +1 for ambiguous requirements.
- +1 for architecture or migration design.
- +1 for high-stakes legal, financial, medical, security, or production risk.
- +1 for debugging without a reproducible failure.
- +1 for adversarial review or formal verification.
- +1 for long-horizon planning with tradeoffs.

Subtract:

- -2 for exact deterministic transformation.
- -1 for simple extraction or formatting.
- -1 when a reliable script fully defines the operation.

Recommendation:

- score <= 0: economy;
- score 1–3: standard;
- score >= 4: powerful.

This is a starting heuristic. Representative evaluations outrank the score.

## 7. Metrics

Track:

- estimated input tokens before and after;
- estimated output tokens;
- cached or fingerprinted context not retransmitted;
- chunks kept, compressed, referenced, and discarded;
- files considered versus opened;
- retries avoided;
- output-contract pass/fail;
- task-quality pass/fail.

Report savings as:

```text
1 - compacted_estimated_tokens / original_estimated_tokens
```

Do not present this as a billing guarantee.
