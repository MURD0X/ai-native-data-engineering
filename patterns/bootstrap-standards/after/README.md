# After: Engineered Pipeline (AI-Safe)

This is the same customer order processing pipeline — same business logic, same output — with engineering discipline applied.

## What's Different

| Practice | Status |
|----------|--------|
| Schema contract | `metadata.yaml` — grain, PII fields, data quality checks |
| Tests | `tests/test_pipeline.py` — grain, PII, calculations |
| Governance metadata | PII masking policy, audit rules |
| Git discipline | Commit history, conventional commits |
| Scheduling metadata | SLA, timing dependencies |

## Run It

```bash
pip install -r requirements.txt
python pipeline.py
```

## Run Tests

```bash
pytest tests/ -v
```

## What This Demonstrates

Give an AI agent the same task on this pipeline and it will:

1. Read `metadata.yaml` before writing any code
2. Add `is_vip_customer` at the correct grain (customer-per-day)
3. Apply PII masking per governance policy
4. Run tests before committing
5. Commit with an auditable message

The agent doesn't behave better because it's smarter. It behaves better because the system gives it the context it needs to make the right decisions.

---

*See [PATTERN.md](../PATTERN.md) for the full story.*
