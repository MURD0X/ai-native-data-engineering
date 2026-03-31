# After: Engineered Pipeline (AI-Safe)

This is the same customer order processing pipeline — same business logic, same output — with engineering discipline applied.

## What's Different

| Practice | How It Works |
|----------|-------------|
| Schema contract | `metadata.yaml` defines grain, field types, VIP threshold — read at runtime by `get_output_config()` |
| Governance metadata | `never_expose_in_outputs` list drives `output_columns` — PII exclusion is structural, not manual |
| Tests | 24 tests including `test_threshold_is_configurable` — proves the metadata contract itself |
| Git discipline | Conventional commits with rationale, agent changes attributed |
| Schedule metadata | Cron + upstream dependencies explicit — agent reads before modifying |

**The key design principle:** The YAML is the contract. The Python is the execution engine. Changing `metadata.yaml` changes runtime behavior without touching code.

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
