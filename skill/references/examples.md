# Examples

## Example 1: Large repository bug

Request: Fix a refresh-token race condition.

Keep:

- public API constraint;
- failing test and exact assertion;
- relevant authentication files and call graph;
- accepted design decision;
- modified diff and test result.

Compress:

- full test logs to command, failure, and key stack frames;
- architecture docs to the relevant locking and token lifecycle passages.

Reference:

- unchanged dependency lockfile;
- full API documentation by path and section.

Discard:

- rejected database-lock approach after recording why it was rejected;
- duplicate stack traces;
- earlier patch superseded by the accepted patch.

## Example 2: Editorial rewrite

Request: Rewrite an 800-word article to exactly 500 words without losing names, dates, quotations, or the central argument.

Keep the source article and exact constraints. Do not load unrelated style guides. Generate one candidate, count words deterministically, and revise only the overage or deficit. Validate exact count before returning. Do not include commentary outside the 500 words.

## Example 3: Five-bullet analysis

Output contract:

- exactly five Markdown bullets;
- each bullet one sentence;
- ordered by severity;
- include evidence path and line range;
- no introduction or conclusion.

Validate bullet count. A five-bullet response plus a preamble is a failure.

## Example 4: Long conversation handoff

Create a fresh continuation:

```text
Goal: Ship the import feature.
Constraints: Preserve CSV compatibility; no schema migration.
Accepted artifact: docs/import-plan-v3.md (sha256: ...).
Decisions: Stream input; reject invalid rows; report row numbers.
Evidence: parser.py L40-L120; tests/test_import.py L12-L88.
Open issue: memory usage above 2 GB files.
Next action: implement streaming parser and run import tests.
```

Exclude the discarded v1/v2 plans, full critiques, and raw benchmark logs.
