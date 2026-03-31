# Before: Legacy Pipeline (Unstructured)

This is a **deliberately unstructured** customer order processing pipeline. It works — but it's not AI-safe.

## What's Missing

- No schema contract (agent can't know grain is customer-per-day)
- No tests (bad changes ship silently)
- No governance metadata (PII fields unprotected)
- No Git discipline (no audit trail, no rollback)
- No scheduling metadata (timing dependencies implicit)

## Run It

```bash
pip install -r requirements.txt
python pipeline.py
```

Produces `daily_summary.csv`.

## What This Demonstrates

Give an AI agent a task on this pipeline and watch it:

1. Add a field at the wrong grain level
2. Expose PII in the output
3. Set a schedule that conflicts with upstream dependencies

None of these are the agent's fault. They're the predictable result of missing engineering context.

---

*See [PATTERN.md](../PATTERN.md) for the full story.*
