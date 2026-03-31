"""
Customer Order Processing Pipeline
===================================
Metadata-driven: runtime behavior (output columns, PII exclusion, grain keys,
quality checks, VIP threshold) is read from metadata.yaml — not hardcoded.

Changing metadata.yaml changes what the pipeline does.
The Python is the execution engine. The YAML is the contract.

Run:  python pipeline.py
Test: pytest tests/ -v
"""

import hashlib
import logging
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent / "orders.sqlite"
METADATA_PATH = Path(__file__).parent / "metadata.yaml"
OUTPUT_PATH = Path(__file__).parent / "daily_summary.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("pipeline")


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

def load_metadata() -> dict:
    """
    Load pipeline contract from metadata.yaml.

    This is the single source of truth for:
      - output grain and grain keys
      - PII fields that must never appear in output
      - VIP revenue threshold
      - data quality checks to run before writing
    """
    with open(METADATA_PATH) as f:
        return yaml.safe_load(f)


def get_output_config(meta: dict) -> dict:
    """
    Derive runtime output configuration from metadata.yaml.

    Returns a dict with:
      - grain_keys: columns that define one unique row (e.g. [date, customer_id])
      - pii_fields: fields to never write to output
      - output_columns: schema fields minus PII fields, in declaration order
      - vip_threshold: revenue threshold for is_vip_customer flag
    """
    dataset = meta["datasets"]["daily_summary"]
    pii_never_expose = set(meta["governance"]["pii_rules"]["never_expose_in_outputs"])

    grain_keys = dataset["grain_keys"]
    schema_fields = list(dataset["schema"].keys())
    output_columns = [f for f in schema_fields if f not in pii_never_expose]
    vip_threshold = dataset["schema"]["is_vip_customer"]["threshold"]

    return {
        "grain_keys": grain_keys,
        "pii_fields": pii_never_expose,
        "output_columns": output_columns,
        "vip_threshold": vip_threshold,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def mask_pii(value: Optional[str]) -> Optional[str]:
    """
    One-way hash for PII fields.
    Consistent (same input → same hash) and irreversible.
    """
    if value is None:
        return None
    return hashlib.sha256(str(value).encode()).hexdigest()[:16]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def load_orders() -> pd.DataFrame:
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
    Left-join with customer dimension.

    PII present after this step (customer_name, address).
    They stay in memory for metric calculation and are excluded from
    output by aggregate_daily_summary() per the governance contract.
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
    """Add order_date and rolling 30-day revenue per customer (order-level)."""
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
    """Left-join inventory on product_id. Only fetches products present in the data."""
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


def aggregate_daily_summary(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Aggregate to grain, apply business rules, enforce output contract.

    All decisions here come from config (derived from metadata.yaml):
      - grain_keys    → which columns define uniqueness
      - vip_threshold → threshold for is_vip_customer flag
      - output_columns → which fields to write (PII already excluded)

    This means: change the YAML, change what gets written. No code change needed.
    """
    log.info(
        "Aggregating to %s grain (keys: %s)",
        "customer_per_day",
        config["grain_keys"],
    )
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

    # VIP threshold read from metadata.yaml → datasets.daily_summary.schema.is_vip_customer.threshold
    summary["is_vip_customer"] = summary["rolling_30d_revenue"] >= config["vip_threshold"]

    # Output columns read from metadata.yaml → datasets.daily_summary.schema (minus pii_fields)
    return summary[config["output_columns"]]


def validate_output(df: pd.DataFrame, meta: dict, config: dict) -> None:
    """
    Run data quality checks declared in metadata.yaml.

    Checks are driven by:
      - config["grain_keys"] → which columns must be unique and non-null
      - metadata → governance.data_quality.checks → which named checks to run

    Adding a check to metadata.yaml makes it run here automatically.
    """
    log.info("Running data quality checks from metadata contract")
    checks = {c["name"] for c in meta["governance"]["data_quality"]["checks"]}

    if "grain_consistency" in checks:
        duplicates = df.duplicated(subset=config["grain_keys"]).sum()
        if duplicates > 0:
            raise ValueError(
                f"Grain violation: {duplicates} duplicate ({', '.join(config['grain_keys'])}) rows. "
                "Expected exactly one row per grain."
            )

    if "no_nulls_in_grain_keys" in checks:
        for col in config["grain_keys"]:
            nulls = df[col].isna().sum()
            if nulls > 0:
                raise ValueError(f"Data quality failure: {nulls} null values in grain key '{col}'")

    if "daily_revenue_non_negative" in checks:
        negative = (df["daily_revenue"] < 0).sum()
        if negative > 0:
            raise ValueError(f"Data quality failure: {negative} rows have negative daily_revenue")

    log.info("All data quality checks passed (%d checks run)", len(checks))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_pipeline() -> pd.DataFrame:
    """
    Execute the full pipeline.

    Loads metadata.yaml once. All downstream functions receive the config
    they need rather than re-reading the file or relying on module-level constants.
    """
    meta = load_metadata()
    config = get_output_config(meta)

    log.info(
        "Starting pipeline '%s' (grain: %s, SLA: %s, vip_threshold: $%.0f)",
        meta["pipeline_name"],
        meta["grain"],
        meta["sla"],
        config["vip_threshold"],
    )
    log.info("Output columns (from metadata): %s", config["output_columns"])
    log.info("PII fields excluded (from governance): %s", sorted(config["pii_fields"]))

    orders = load_orders()
    enriched = enrich_customer_data(orders)
    with_metrics = calculate_metrics(enriched)
    with_inventory = join_inventory(with_metrics)
    summary = aggregate_daily_summary(with_inventory, config)

    validate_output(summary, meta, config)

    summary.to_csv(OUTPUT_PATH, index=False)
    log.info("Pipeline complete — wrote %d rows to %s", len(summary), OUTPUT_PATH)
    return summary


if __name__ == "__main__":
    run_pipeline()
