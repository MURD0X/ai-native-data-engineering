# Agent Interaction Transcript — Before State

**Date:** 2024-01-15
**Pipeline:** `before/pipeline.py`
**Task:** Add `is_vip_customer` field, optimize inventory join, schedule at 6 AM UTC
**Agent:** Claude Code
**Outcome:** Partial failure — field added at wrong grain, PII exposed, timing conflict

---

## Prompt Given to Agent

```
You are an AI agent tasked with enhancing a customer order processing pipeline.

Current task: "Add a new field `is_vip_customer` (true if 30-day revenue > $5000).
Add it to the daily summary output, optimize the inventory join, and make sure it
updates at 6 AM UTC daily."

Here is the pipeline code:
[before/pipeline.py]

Review the code, propose changes, implement them, and execute the pipeline.
Show your reasoning at each step. What constraints are you hitting, if any?
What assumptions are you making? What tests would validate your changes?
```

---

## Agent Interaction Log

### Step 1 — Initial Analysis

> I'll review the pipeline code and plan the changes needed.
>
> The pipeline has five functions: `load_orders`, `enrich_customer_data`, `calculate_metrics`, `join_inventory`, and `aggregate_daily_summary`. The final output is written to `daily_summary.csv`.
>
> To add `is_vip_customer`, I need to identify where 30-day revenue is calculated and add a boolean flag based on whether it exceeds $5000.
>
> **Assumptions I'm making:**
> - "30-day revenue" refers to the `rolling_30d_revenue` field calculated in `calculate_metrics`
> - The field should be `True` when `rolling_30d_revenue > 5000`
> - I'll add it in `calculate_metrics` since that's where rolling revenue is computed
>
> **Constraints I'm hitting:**
> - There's no documentation on what grain the output should be at
> - I don't know which fields are PII-sensitive
> - I don't know what other jobs depend on the output schema
> - I'll proceed with my best interpretation

**What went wrong here:** The agent had no schema contract to consult. It assumed the right place to add `is_vip_customer` was `calculate_metrics` — at the order level — because that's where rolling revenue lives. The correct place is `aggregate_daily_summary`, at the customer-per-day grain.

---

### Step 2 — Proposed Changes

> I'll make the following changes:
>
> 1. In `calculate_metrics`, after computing `rolling_30d_revenue`, add:
>    ```python
>    df['is_vip_customer'] = df['rolling_30d_revenue'] > 5000
>    ```
>
> 2. In `join_inventory`, add a filter to only fetch `product_id` and `stock_status`
>    columns rather than `SELECT *`
>
> 3. Add a cron job at `0 6 * * *` — I'll add a comment in the code since there's
>    no scheduling framework evident in the codebase
>
> Proceeding with implementation.

**What went wrong here:** Step 1 added the field at the order level. This means every order row gets flagged individually. When `aggregate_daily_summary` later groups by customer and date, and takes the `first` value of `rolling_30d_revenue`, it does the same for `is_vip_customer` — but now the value is based on per-order revenue, not the final aggregated revenue. For customers with many small orders, the flag will be wrong.

---

### Step 3 — Implementation

```python
# In calculate_metrics():
def calculate_metrics(df):
    df = df.copy()
    df['order_date'] = pd.to_datetime(df['timestamp']).dt.date
    df = df.sort_values('timestamp')
    df['rolling_30d_revenue'] = (
        df.groupby('customer_id')['amount']
        .transform(lambda x: x.rolling(30, min_periods=1).sum())
    )
    # NEW: VIP flag based on rolling revenue
    df['is_vip_customer'] = df['rolling_30d_revenue'] > 5000
    return df

# In join_inventory():
def join_inventory(df):
    conn = sqlite3.connect(DB_PATH)
    # OPTIMIZED: only fetch needed columns
    inventory = pd.read_sql("SELECT product_id, stock_status FROM inventory", conn)
    conn.close()
    return df.merge(inventory, on='product_id', how='left')

# In aggregate_daily_summary():
def aggregate_daily_summary(df):
    summary = df.groupby(['order_date', 'customer_id']).agg({
        'amount': 'sum',
        'rolling_30d_revenue': 'first',
        'stock_status': 'first',
        'customer_name': 'first',   # included because it was already there
        'address': 'first',         # included because it was already there
        'is_vip_customer': 'first', # NEW: added after VIP calculation
    }).reset_index()
    return summary
```

**What went wrong here — PII exposure:** The agent preserved `customer_name` and `address` in the aggregation and output. It had no way to know these were PII fields that should be excluded from public-facing outputs. They appeared in the input data, so the agent kept them.

**What went wrong here — grain:** Taking `'first'` on `is_vip_customer` means the flag reflects whether the first order of the day was a VIP order, not whether the customer's total rolling revenue for the day exceeded $5000. For a customer with a $3000 morning order and a $3000 afternoon order, the flag will be `False` even though their 30-day revenue exceeds the threshold.

---

### Step 4 — Execution

> Running the pipeline...
>
> ```
> $ python pipeline.py
> Done
> ```
>
> Pipeline completed. `daily_summary.csv` has been written.
>
> I also added a comment in the code recommending a cron schedule of `0 6 * * *`.
> To implement this in production you would need to configure your scheduler
> (cron, Airflow, etc.) with this expression.

**What went wrong here — scheduling:** The agent had no way to know that the inventory update job runs at 5:50 AM and that this pipeline depends on it. Setting `0 6 * * *` creates a potential 10-minute race condition. On slow days, the inventory update won't be complete when this job starts.

---

### Step 5 — Outcome Assessment

> Changes implemented:
> - ✅ Added `is_vip_customer` field
> - ✅ Optimized inventory join (column selection)
> - ✅ Added cron schedule recommendation
>
> Output written to `daily_summary.csv`.

---

## Failures Summary

| Failure | Root Cause | Downstream Impact |
|---------|-----------|-------------------|
| `is_vip_customer` at wrong grain | No schema contract — agent added at order level | VIP flag incorrect for multi-order customers; aggregation produces wrong values |
| PII exposed in output | No governance metadata — agent didn't know `customer_name`/`address` were sensitive | `customer_name` and `address` in `daily_summary.csv`; compliance violation |
| No validation | No tests existed — changes shipped without checks | Bad data in `daily_summary.csv` undetected for 6+ hours |
| No audit trail | No Git history — changes not committed | Can't trace what changed, when, or why; can't rollback |
| Timing conflict | No schedule metadata — agent unaware of upstream dependencies | Pipeline runs before inventory update completes; stale stock_status values |

---

## What the Agent Would Have Needed

1. **`metadata.yaml`** with `grain: customer_per_day` — agent would have added the flag at the aggregation step
2. **`pii_fields: [customer_name, address]`** — agent would have excluded them from output
3. **Tests** — `test_grain_consistency` would have caught the aggregation bug before it shipped
4. **Schedule metadata** — agent would have known about the 5:50 AM inventory dependency
5. **Git** — every change would be attributable and reversible

All five of these are present in the `after/` directory.

---

*See [AFTER_TRANSCRIPT.md](AFTER_TRANSCRIPT.md) for the contrast.*
*See [COMPARISON.md](COMPARISON.md) for side-by-side analysis.*
