<div align="center">

# AI-Native Data Systems

**Engineering discipline is the prerequisite for AI-safe data pipelines.**

[![Tests](https://img.shields.io/badge/tests-24%20passing-0f6e56?style=flat-square)](patterns/bootstrap-standards/after/tests/)
[![Patterns](https://img.shields.io/badge/patterns-1%20complete-0f6e56?style=flat-square)](patterns/)
[![License](https://img.shields.io/badge/license-MIT-6e7681?style=flat-square)](LICENSE)

<br>

*"Unstructured data breaks AI in days, humans in months.<br>The solution isn't more AI — it's engineering discipline that makes AI safe."*

<br>

🌐 **[murd0x.github.io/ai-native-data-engineering](https://murd0x.github.io/ai-native-data-engineering/)** — live site

**[→ Open the Interactive Explorer](https://murd0x.github.io/ai-native-data-engineering/patterns/bootstrap-standards/interactive/index.html)** · [Read the Pattern](patterns/bootstrap-standards/PATTERN.md) · [View the Code](patterns/bootstrap-standards/)

</div>

---

## What this is

A public pattern library for senior data engineers, platform architects, and engineering leaders deploying AI agents on data infrastructure.

Each pattern is a **minimal but complete example system** — real working code, real tests, real agent interaction transcripts — that answers a specific question about making data pipelines AI-safe. The proof is interactive, not narrative.

This is not a framework. It's not a platform. It's a set of concrete, clonable examples that show exactly what engineering discipline looks like in practice — and exactly what happens when it's missing.

---

## The problem

A data team deployed an AI copilot on their warehouse. The first task was routine: add a VIP customer flag, optimize a join, reschedule to 6 AM UTC. The agent reported success.

Six hours later, revenue figures were inflated 5–10×. Customer names and addresses had leaked into a public-facing dashboard. Three downstream jobs had failed silently.

The postmortem said: *"AI isn't ready for production data engineering."*

**That conclusion was wrong.**

The agent didn't fail. The data engineering wasn't done.

---

## The diagnosis

Five engineering gaps. Five predictable failures. None of them AI's fault.

| # | Missing | What the agent did | What happened |
|---|---------|-------------------|---------------|
| 1 | Schema contract | Added `is_vip_customer` at order level (no grain definition to consult) | Revenue inflated 5–10× for multi-order customers |
| 2 | Governance metadata | Preserved `customer_name` and `address` in output (no PII rules existed) | Compliance violation, public dashboard exposure |
| 3 | Tests | Shipped changes after Python ran without exception | Grain violation and PII leak undetected for 6 hours |
| 4 | Git discipline | Overwrote the file with no version control | No audit trail, no rollback, no attribution |
| 5 | Schedule metadata | Set `0 6 * * *` without knowing upstream jobs run at 5:50 AM | Race condition, stale data in reports |

> Every one of these is a constraint the agent would have respected — if it had existed.

---

## The insight

The difference isn't documentation. It's that the **pipeline reads its own contract at runtime**.

```python
# before/pipeline.py — behavior hardcoded, invisible to the agent
def aggregate_daily_summary(df):
    # grain is implicit — nobody said customer-per-day
    # PII fields are unknown — customer_name stays in output
    # threshold is a magic number — hardcoded 5000 buried in code
    ...
```

```python
# after/pipeline.py — behavior derived from metadata.yaml at startup
def get_output_config(meta: dict) -> dict:
    pii = set(meta['governance']['pii_rules']['never_expose_in_outputs'])
    fields = list(meta['datasets']['daily_summary']['schema'].keys())
    return {
        'grain_keys':     meta['datasets']['daily_summary']['grain_keys'],
        'output_columns': [f for f in fields if f not in pii],   # PII excluded structurally
        'vip_threshold':  meta['datasets']['daily_summary']['schema']['is_vip_customer']['threshold'],
    }
```

Change `metadata.yaml` — grain, PII rules, VIP threshold, quality checks — and the pipeline behavior changes on the next run. No code edit. No agent review. **The system is safe by construction.**

---

## Patterns

### [Bootstrap Standards](patterns/bootstrap-standards/) — Complete

> What's the minimum engineering baseline that makes a pipeline AI-safe?

A customer order processing pipeline built twice — once without engineering discipline, once with. The same agent runs the same task on both. One fails across five dimensions. One succeeds. The only difference is a YAML file and a test suite.

**What's inside:**

```
patterns/bootstrap-standards/
├── before/
│   └── pipeline.py          # Working code, no discipline — the failure state
├── after/
│   ├── pipeline.py          # Metadata-driven — YAML is the contract
│   ├── metadata.yaml        # Grain, PII rules, threshold, quality checks, schedule
│   └── tests/               # 24 tests — validates the metadata contract itself
├── agent-run/
│   ├── BEFORE_TRANSCRIPT.md # Step-by-step: what the agent did, why it failed
│   ├── AFTER_TRANSCRIPT.md  # Step-by-step: what the agent did, why it succeeded
│   └── COMPARISON.md        # Side-by-side analysis of 6 decision points
└── interactive/             # Single-page HTML explorer — the centerpiece
```

**[→ Open the interactive explorer](https://murd0x.github.io/ai-native-data-engineering/patterns/bootstrap-standards/interactive/index.html)**

---

## The five practices

These aren't new ideas. They're existing practices that become non-negotiable when AI agents are in the loop.

**1. Schema contracts** — A machine-readable definition of your output: grain, fields, types, constraints. Not for documentation — for the pipeline to read and enforce at runtime.

**2. Governance metadata** — Which fields are PII. What the masking policy is. Enforced structurally so agents can't accidentally expose what they don't know is sensitive.

**3. Tests** — Grain consistency, PII masking, business logic, and the metadata contract itself. The pipeline's immune system. Agents run them before committing.

**4. Git discipline** — Every change attributed, timestamped, reversible. The commit message is the agent's reasoning, persisted. Future engineers and agents can read *why*, not just *what*.

**5. Schedule metadata** — Cron expressions and timing dependencies in a file, not just in a scheduler. Agents read it. They can recognize when a constraint is already satisfied.

---

## Quick start

```bash
git clone https://github.com/MURD0X/ai-native-data-engineering.git
cd ai-native-data-engineering

# Generate sample database (45 days of realistic order data)
python3 scripts/generate_sample_db.py

# Run the engineered pipeline
cd patterns/bootstrap-standards/after
pip install -r requirements.txt
python3 pipeline.py

# Run the tests
pytest tests/ -v

# Open the interactive explorer locally
cd ../interactive
python3 -m http.server 8080
# → http://localhost:8080
```

---

## Who this is for

**Data engineers** evaluating AI copilots for warehouse work — use the `after/` directory as a template for your own pipelines.

**Platform architects** defining standards before deploying agents — use the five practices as a checklist. Each one has a concrete implementation here.

**Engineering leaders** making the case for discipline — use the before/after comparison. The interactive explorer makes the failure modes visible in 10 minutes.

---

## Philosophy

AI agents are not uniquely dangerous. They're uniquely fast at finding gaps.

A pipeline without tests works fine under human oversight for months. The same pipeline with an AI copilot surfaces every edge case in its first week. The corner you cut in 2023 becomes a production incident in 2024 when the agent finds it.

**The practices that make systems safe for humans also make them safe for AI. Everything else is acceleration.**

You don't need a metadata platform to start. A YAML file with your grain and PII fields, one grain-consistency test, and a `.gitignore` is already a meaningfully safer system than what most teams have today.

---

## Contributing

Each pattern is self-contained. See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add a new pattern.

---

## License

MIT
