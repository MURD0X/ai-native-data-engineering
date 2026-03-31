"""
Customer Order Processing Pipeline
===================================
Grain:   customer_per_day (one row per customer per calendar day)
Owner:   data-platform-team
SLA:     06:00 UTC daily
Metadata: metadata.yaml

Run:     python pipeline.py
Test:    pytest tests/ -v
"""

import hashlib
import logging
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent / "orders.sqlite"
METADATA_PATH = Path(__file__).parent / "metadata.yaml"
OUTPUT_PATH = Path(__file__).parent / "daily_summary.csv"
VIP_REVENUE_THRESHOLD = 5_000.00

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("pipeline")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_metadata() -> dict:
    """Load and return pipeline metadata from metadata.yaml."""
    with open(METADATA_PATH) as f:
        return yaml.safe_load(f)


def mask_pii(value: Optional[str]) -> Optional[str]:
    """
    One-way hash for PII fields exposed in public outputs.
    Consistent: same input always produces same hash (for joinability).
    Irreversible: original value cannot be recovered from hash.
    """
    if value is None:
        return None
    return hashlib.sha256(str(value).encode()).hexdigest()[:16]


def get_connection() -> sqlite3.Connection:
    """Return a read-only SQLite connection."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def load_orders() -> pd.DataFrame:
    """
    Load raw orders from the orders table.

    Returns
    -------
    pd.DataFrame with columns: order_id, customer_id, product_id, amount,
        timestamp, payment_method
    """
    log.info("Loading orders from %s", DB_PATH)
    with get_connection() as conn:
        df = pd.read_sql(
            "SELECT order_id, customer_id, product_id, amount, timestamp, payment_method FROM orders",
            conn,
            parse_dates=["timestamp"],
        )
    log.info("Loaded %d orders", len(df))
    return df


# ---------------------------------------------------------------------------
# Transformation
# ---------------------------------------------------------------------------

def enrich_customer_data(orders_df: pd.DataFrame) -> pd.DataFrame:
    """
    Left-join orders with the customer dimension table.

    PII NOTE: The returned DataFrame will contain customer_name and address.
    These fields must be masked or dropped before any public-facing output.
    See metadata.yaml → governance.pii_rules for the masking policy.

    Parameters
    ----------
    orders_df : pd.DataFrame
        Raw orders, must include customer_id.

    Returns
    -------
    pd.DataFrame with PII fields present (for internal calculation use only).
    """
    log.info("Enriching orders with customer data")
    with get_connection() as conn:
        customers = pd.read_sql(
            "SELECT customer_id, customer_name, address FROM customers",
            conn,
        )
    enriched = orders_df.merge(customers, on="customer_id", how="left")
    missing = enriched["customer_name"].isna().sum()
    if missing > 0:
        log.warning("%d orders have no matching customer record", missing)
    return enriched


def calculate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add order_date and rolling 30-day revenue per customer.

    Rolling revenue is computed at the order level here. The final
    customer-per-day value is taken as the last value in the aggregation step,
    consistent with the grain defined in metadata.yaml.

    Parameters
    ----------
    df : pd.DataFrame
        Enriched orders with a timestamp column.

    Returns
    -------
    pd.DataFrame with added columns: order_date, rolling_30d_revenue.
    """
    log.info("Calculating revenue metrics")
    df = df.copy()
    df["order_date"] = df["timestamp"].dt.normalize()
    df = df.sort_values(["customer_id", "timestamp"])

    df["rolling_30d_revenue"] = (
        df.groupby("customer_id")["amount"]
        .transform(lambda x: x.rolling(30, min_periods=1).sum())
    )
    return df


def join_inventory(df: pd.DataFrame) -> pd.DataFrame:
    """
    Left-join inventory data on product_id to attach stock_status.

    Optimization: only fetches product_id and stock_status columns to minimise
    data transfer. Products not found in inventory default to 'unknown'.

    Parameters
    ----------
    df : pd.DataFrame
        Orders with product_id column.

    Returns
    -------
    pd.DataFrame with stock_status column added.
    """
    log.info("Joining inventory data")
    product_ids = df["product_id"].unique().tolist()
    placeholders = ",".join("?" * len(product_ids))
    with get_connection() as conn:
        inventory = pd.read_sql(
            f"SELECT product_id, stock_status FROM inventory WHERE product_id IN ({placeholders})",
            conn,
            params=product_ids,
        )
    result = df.merge(inventory, on="product_id", how="left")
    result["stock_status"] = result["stock_status"].fillna("unknown")
    return result


def aggregate_daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate to customer-per-day grain, apply PII masking, add VIP flag.

    Grain: one row per (date, customer_id) — see metadata.yaml.
    PII:   customer_name and address are masked per governance policy.
           They are NOT included in the final output.

    Parameters
    ----------
    df : pd.DataFrame
        Order-level data with order_date, customer_id, amount,
        rolling_30d_revenue, stock_status.

    Returns
    -------
    pd.DataFrame with columns: date, customer_id, daily_revenue,
        rolling_30d_revenue, stock_status, is_vip_customer.
    """
    log.info("Aggregating to customer-per-day grain")
    summary = (
        df.groupby(["order_date", "customer_id"])
        .agg(
            daily_revenue=("amount", "sum"),
            rolling_30d_revenue=("rolling_30d_revenue", "last"),
            stock_status=("stock_status", "first"),
        )
        .reset_index()
        .rename(columns={"order_date": "date"})
    )

    # VIP flag — evaluated at correct grain (customer-per-day rolling revenue)
    summary["is_vip_customer"] = summary["rolling_30d_revenue"] >= VIP_REVENUE_THRESHOLD

    # Enforce column order and exclude PII fields from output
    output_columns = [
        "date", "customer_id", "daily_revenue",
        "rolling_30d_revenue", "stock_status", "is_vip_customer",
    ]
    return summary[output_columns]


def validate_output(df: pd.DataFrame) -> None:
    """
    Run data quality checks from metadata.yaml before writing output.

    Raises
    ------
    ValueError if any quality check fails.
    """
    log.info("Running data quality checks")

    # Check grain consistency: no duplicate (date, customer_id) pairs
    duplicates = df.duplicated(subset=["date", "customer_id"]).sum()
    if duplicates > 0:
        raise ValueError(
            f"Grain violation: {duplicates} duplicate (date, customer_id) rows found. "
            "Expected exactly one row per customer per day."
        )

    # Check no nulls in grain keys
    for col in ["date", "customer_id"]:
        nulls = df[col].isna().sum()
        if nulls > 0:
            raise ValueError(f"Data quality failure: {nulls} null values in grain key '{col}'")

    # Check revenue non-negative
    negative = (df["daily_revenue"] < 0).sum()
    if negative > 0:
        raise ValueError(f"Data quality failure: {negative} rows have negative daily_revenue")

    log.info("All data quality checks passed")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_pipeline() -> pd.DataFrame:
    """
    Execute the full pipeline and return the daily summary DataFrame.

    Steps:
        1. Load orders
        2. Enrich with customer data (PII present internally)
        3. Calculate rolling 30-day revenue metrics
        4. Join inventory for stock status
        5. Aggregate to customer-per-day grain, mask PII, add VIP flag
        6. Validate output quality
        7. Write to CSV

    Returns
    -------
    pd.DataFrame — the validated daily summary.
    """
    metadata = load_metadata()
    log.info(
        "Starting pipeline '%s' (grain: %s, SLA: %s)",
        metadata["pipeline_name"],
        metadata["grain"],
        metadata["sla"],
    )

    orders = load_orders()
    enriched = enrich_customer_data(orders)
    with_metrics = calculate_metrics(enriched)
    with_inventory = join_inventory(with_metrics)
    summary = aggregate_daily_summary(with_inventory)

    validate_output(summary)

    summary.to_csv(OUTPUT_PATH, index=False)
    log.info("Pipeline complete — wrote %d rows to %s", len(summary), OUTPUT_PATH)
    return summary


if __name__ == "__main__":
    run_pipeline()
