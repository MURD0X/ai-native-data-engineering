# AI-Native Data Systems

> "Unstructured data breaks AI in days, humans in months. The solution isn't more AI — it's engineering discipline that makes AI safe."

A public-facing guide for senior data engineers, platform architects, and engineering leaders who want to deploy AI agents safely on their data systems.

## What This Is

This project is a collection of **patterns** — minimal but complete example systems that prove engineering philosophy through interactive experience, not just narrative.

Each pattern answers a specific question about how AI agents interact with data infrastructure — and shows, concretely, what engineering discipline makes the difference between failure and success.

## Patterns

| Pattern | Question | Status |
|---------|----------|--------|
| [Bootstrap Standards](patterns/bootstrap-standards/) | What's the minimum engineering baseline that makes a pipeline AI-safe? | Complete |

## Quick Start

```bash
git clone https://github.com/your-org/ai-native-data-systems
cd ai-native-data-systems

# Generate sample data
python3 scripts/generate_sample_db.py

# Run the engineered pipeline
cd patterns/bootstrap-standards/after
pip install -r requirements.txt
python3 pipeline.py

# Run the tests
pytest tests/ -v

# Open the interactive explorer
cd ../interactive
python3 -m http.server 8080
# → http://localhost:8080
```

## Core Thesis

AI agents are uniquely good at exposing every shortcut you took:

- No schema contract → agent doesn't understand grain, breaks aggregations
- No tests → bad changes ship silently, PII leaks go undetected
- No governance metadata → agent can't apply masking policies
- No Git discipline → no audit trail, no rollback, no accountability
- No schedule management → SLA violations, missed reports, eroded trust

The practices that make systems safe for humans also make them safe for AI. The difference is that AI finds the gaps much faster.

## Who This Is For

- **Data engineers** who are evaluating AI copilots for warehouse work
- **Platform architects** who need to define standards before deploying agents
- **Engineering leaders** who need to make the case for engineering discipline

## How to Use This

Start with the first pattern: [Bootstrap Standards](patterns/bootstrap-standards/).

Read the [narrative guide](patterns/bootstrap-standards/PATTERN.md), then explore the [interactive comparison](patterns/bootstrap-standards/interactive/index.html).

Clone the `after/` directory in any pattern and use it as a template for your own pipelines.

## Contributing

Each pattern is self-contained. To add a new pattern, copy the directory structure from `patterns/bootstrap-standards/` and follow the same conventions.

## License

MIT

---

*The practices that make systems safe for humans also make them safe for AI. Everything else is acceleration.*
