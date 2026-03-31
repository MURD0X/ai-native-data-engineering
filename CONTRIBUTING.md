# Contributing a Pattern

Each pattern in this project answers a specific question about AI safety in data engineering — through working code, not narrative alone.

---

## What makes a good pattern

A pattern should:

- **Answer one question** — narrow, specific, answerable with a minimal example
- **Work end-to-end** — real code that runs, not pseudocode
- **Show the failure** — the before state should demonstrate a real, predictable failure mode
- **Show the fix** — the after state should show the minimal engineering that prevents it
- **Be interactive** — an HTML explorer that makes the contrast visible without reading code

Good candidate questions:
- *What's the minimum schema needed before running an agent on a dbt model?*
- *How do you test an AI-modified SQL transform for correctness?*
- *What does a safe agent handoff look like for a multi-step pipeline?*

---

## Pattern structure

```
patterns/your-pattern-name/
├── PATTERN.md              # Narrative guide (5-10 min read)
├── before/
│   ├── README.md           # "This is the failure state"
│   ├── pipeline.py         # Working code, no discipline
│   └── requirements.txt
├── after/
│   ├── README.md           # "This is engineered"
│   ├── pipeline.py         # Same logic, metadata-driven
│   ├── metadata.yaml       # Schema contract, governance, schedule
│   ├── tests/
│   │   └── test_pipeline.py
│   └── requirements.txt
├── agent-run/
│   ├── BEFORE_TRANSCRIPT.md
│   ├── AFTER_TRANSCRIPT.md
│   └── COMPARISON.md
└── interactive/
    ├── index.html
    ├── index.js
    ├── styles.css
    └── data.json
```

The [bootstrap-standards](patterns/bootstrap-standards/) pattern is the reference implementation — copy its structure as a starting point.

---

## The metadata-driven principle

The `after/` pipeline should actually read its contract at runtime, not just have a YAML file sitting next to it. The pipeline should derive:

- Output columns from the schema definition
- PII exclusion from `governance.pii_rules.never_expose_in_outputs`
- Business rule thresholds from the schema
- Quality checks from `governance.data_quality.checks`

Changing the YAML should change the behavior. No code edit required.

---

## Before you open a PR

- [ ] The before pipeline actually runs and produces output
- [ ] The after pipeline actually runs and all tests pass
- [ ] The HTML explorer loads from `interactive/` with `python3 -m http.server`
- [ ] `data.json` reflects the current code (not an earlier draft)
- [ ] `PATTERN.md` is written after the code, not before
- [ ] Git history shows the evolution (before → metadata → tests → pipeline → explorer → narrative)

---

## Scope guidelines

- **Keep it minimal** — 3-5 transformations, not 20
- **Keep it generic** — no proprietary systems, no company-specific details
- **Keep it real** — code that actually runs on a cloned repo
- **Keep it focused** — one failure mode well-demonstrated beats five failure modes sketched

---

## Opening a PR

1. Fork the repo
2. Create a branch: `patterns/your-pattern-name`
3. Build the pattern following the structure above
4. Push the branch and open a PR against `main`
5. Include in the PR description: the question your pattern answers, what the before failure is, what the after fix is, and test results

Questions? Open an issue.
