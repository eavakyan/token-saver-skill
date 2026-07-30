# Token Saver examples

## Compact input

```json
{
  "request": "Fix the refresh-token race without changing the public API.",
  "chunks": [
    {"id": "request", "kind": "current_request", "text": "Fix the refresh-token race."},
    {"id": "constraint", "kind": "constraint", "text": "Do not change the public API."},
    {"id": "decision", "kind": "decision", "text": "Use a per-user lock."},
    {"id": "proof", "kind": "evidence", "text": "The concurrency test reproduces the duplicate refresh.", "metadata": {"essential": true}},
    {"id": "code", "kind": "code", "text": "def refresh(): ...", "source": "app/auth.py:40", "metadata": {"reopenable": true}},
    {"id": "old", "kind": "draft", "text": "Abandoned implementation...", "metadata": {"superseded": true}}
  ]
}
```

Run:

```bash
token-saver compact --input context.json --output handoff.json --save-handoff
```

Expected properties:

- The request, constraint, decision, and essential evidence remain.
- Verified-reopenable code becomes an exact source reference rather than a paraphrase; unverified code remains verbatim.
- The abandoned draft is absent from `context` and its raw text is never emitted.
- `status=infeasible` appears if protected content alone exceeds the budget.

## Resume

```bash
token-saver handoff show
token-saver artifact show --accepted
```

Use only the saved handoff, accepted artifact, current request, and newly retrieved evidence. Reopen referenced sources when exact contents are needed.
