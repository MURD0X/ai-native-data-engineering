# Before vs. After: Side-by-Side Comparison

**Task:** Add `is_vip_customer` field, optimize inventory join, schedule at 6 AM UTC

---

## Decision Point 1: First Action

| | Before | After |
|---|--------|-------|
| **Agent's first action** | Read the code, form assumptions | Read `metadata.yaml` before reading code |
| **Why** | No metadata to consult | Metadata existed and was the right starting point |
| **Impact** | Agent proceeded on assumptions about grain | Agent proceeded on documented facts about grain |

---

## Decision Point 2: Where to Add is_vip_customer

| | Before | After |
|---|--------|-------|
| **Where field was added** | `calculate_metrics()` — order level | `aggregate_daily_summary()` — customer-per-day level |
| **Why** | No grain constraint → agent added it where rolling revenue was computed | Metadata said `grain: customer_per_day` → agent added it at aggregation |
| **Result** | Field reflects per-order rolling revenue, not customer-day revenue | Field reflects correct aggregated 30-day revenue per customer per day |
| **Downstream impact** | Customers with multiple orders get wrong VIP flag; inflated aggregations | All customers get correct VIP flag regardless of order count |
| **Constraint that made the difference** | None (missing) | `metadata.yaml → grain: customer_per_day` |

---

## Decision Point 3: PII in Output

| | Before | After |
|---|--------|-------|
| **customer_name in output** | Yes — present in `daily_summary.csv` | No — excluded per governance policy |
| **address in output** | Yes — present in `daily_summary.csv` | No — excluded per governance policy |
| **Why** | No governance metadata → agent didn't know these were sensitive | `metadata.yaml → governance.pii_rules.never_expose_in_outputs` |
| **Result** | Compliance violation; PII in public-facing CSV | Clean output; no PII exposure |
| **Constraint that made the difference** | None (missing) | `metadata.yaml → governance.pii_rules` |

---

## Decision Point 4: Validation Before Shipping

| | Before | After |
|---|--------|-------|
| **Tests run before committing** | No — no tests existed | Yes — `pytest tests/ -v` ran 20 tests |
| **Grain test** | N/A | Passed — `test_two_orders_same_customer_same_day_produce_one_row` |
| **PII test** | N/A | Passed — `test_customer_name_not_in_output_columns` |
| **VIP test** | N/A | Passed — `test_vip_evaluated_at_customer_day_grain_not_order_level` |
| **Result** | Broken data shipped silently | All validations passed; change deployed with confidence |
| **Constraint that made the difference** | None (missing) | `tests/test_pipeline.py` |

---

## Decision Point 5: Scheduling

| | Before | After |
|---|--------|-------|
| **What agent did** | Added comment suggesting `0 6 * * *` | Read schedule metadata; confirmed `0 6 * * *` already configured |
| **Did agent know about upstream dependencies?** | No | Yes — `depends_on: inventory_update (05:50 UTC)` in metadata |
| **Risk created** | Race condition if inventory runs late | None — agent recognized constraint was already satisfied |
| **Result** | Potential timing conflict on slow days | No change; correct timing preserved |
| **Constraint that made the difference** | None (missing) | `metadata.yaml → schedule.depends_on` |

---

## Decision Point 6: Audit Trail

| | Before | After |
|---|--------|-------|
| **Git commit created** | No | Yes |
| **Commit message quality** | N/A | Detailed: grain decision, PII policy, test count, schedule rationale |
| **Reversibility** | None — no way to undo | `git revert <hash>` |
| **Accountability** | Unknown who changed what | Agent identity, timestamp, reasoning all in Git history |
| **Constraint that made the difference** | None (missing) | Git + conventional commits |

---

## Overall Outcome

| Dimension | Before | After |
|-----------|--------|-------|
| Feature correctness | Partial — field exists but at wrong grain | Full — field at correct grain with correct values |
| Data integrity | Violated — duplicate revenue counts | Maintained — clean aggregation |
| Compliance | Violated — PII in output | Maintained — PII excluded per policy |
| Validation | None | 20 tests all passing |
| Auditability | None | Full Git history with context |
| Schedule integrity | At risk | Preserved |

---

## The Key Insight

The agent didn't fail in the before state because it was unintelligent or careless. It failed because **it operated without context**.

The after state didn't succeed because the agent was smarter. It succeeded because **the system gave the agent the information it needed to make the right decisions**.

Schema contracts, governance metadata, tests, and scheduling metadata aren't constraints on the agent — they're communication from the engineering team to the agent. The agent acts on whatever information it's given. What you give it determines what it does.

> "Unstructured systems break AI in days, humans in months. AI exposes every corner you cut — just faster."

---

*[Open the interactive explorer](../interactive/index.html) to walk through this comparison visually.*
