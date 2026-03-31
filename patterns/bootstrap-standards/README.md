<div align="center">

# Bootstrap Standards

**What's the minimum engineering baseline that makes a pipeline AI-safe?**

[![Tests](https://img.shields.io/badge/tests-24%20passing-0f6e56?style=flat-square)](after/tests/)

**[→ Open the Interactive Explorer](https://murd0x.github.io/ai-native-data-engineering/patterns/bootstrap-standards/interactive/index.html)**

</div>

---

## The premise

The same agent. The same task. Two pipelines — one unstructured, one engineered.

The task: *"Add `is_vip_customer` (true if 30-day revenue > $5000). Add it to the daily summary, optimize the inventory join, schedule at 6 AM UTC."*

On the unstructured pipeline, the agent fails across five dimensions — not because it's careless, but because the system gives it nothing to be careful with.

On the engineered pipeline, the same agent succeeds on all five — because it can read its own contract.

---

## What's in this pattern

| Directory | What it is |
|-----------|-----------|
| [`before/`](before/) | Working pipeline with no engineering discipline — the failure state |
| [`after/`](after/) | Same business logic, metadata-driven — the YAML is the contract |
| [`agent-run/`](agent-run/) | Step-by-step interaction transcripts and side-by-side comparison |
| [`interactive/`](interactive/) | Single-page HTML explorer — the centerpiece |
| [`PATTERN.md`](PATTERN.md) | 5-8 minute narrative guide |

---

## The five failures (and fixes)

| Constraint | Without it | With it |
|---|---|---|
| **Schema contract** | Agent adds field at order level — wrong grain, inflated revenue | `get_output_config()` returns `grain_keys` at runtime — field added correctly |
| **Governance metadata** | `customer_name` and `address` written to output — PII violation | `never_expose_in_outputs` enforced structurally — PII excluded by construction |
| **Tests** | Broken data ships silently | 24 tests run before commit — grain, PII, and the metadata contract all validated |
| **Git discipline** | No audit trail, no rollback | Full history, every change attributed and reversible |
| **Schedule metadata** | Agent sets cron without knowing upstream timing — race condition | `depends_on` is explicit — agent reads it, constraint already satisfied |

---

## The key design principle

```yaml
# metadata.yaml — the single source of truth
datasets:
  daily_summary:
    grain_keys: [date, customer_id]        # enforced at runtime
    schema:
      is_vip_customer:
        threshold: 5000.00                 # read at runtime — change here, behavior changes
governance:
  pii_rules:
    never_expose_in_outputs:               # drives output_columns at runtime
      - customer_name
      - address
      - email
```

```python
# pipeline reads this on startup — no hardcoded values
config = get_output_config(meta)
# config['grain_keys']     → ['date', 'customer_id']
# config['output_columns'] → schema fields minus PII fields
# config['vip_threshold']  → 5000.0
```

**Changing the YAML changes the behavior. No Python edit required.**

---

## Run it yourself

```bash
# Install dependencies
cd after && pip install -r requirements.txt

# Run the pipeline
python3 pipeline.py

# Run the tests
pytest tests/ -v

# Open the interactive explorer
cd ../interactive && python3 -m http.server 8080
# → http://localhost:8080
```

---

## Read more

- [Full narrative guide →](PATTERN.md)
- [Before transcript — what failed and why →](agent-run/BEFORE_TRANSCRIPT.md)
- [After transcript — what succeeded and why →](agent-run/AFTER_TRANSCRIPT.md)
- [Side-by-side comparison →](agent-run/COMPARISON.md)

---

*Part of [AI-Native Data Systems](../../README.md)*
