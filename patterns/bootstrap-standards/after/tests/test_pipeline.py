"""
Tests for after/pipeline.py

Validates the five constraints that make this pipeline AI-safe:
  1. Grain consistency  — exactly one row per (date, customer_id)
  2. PII not exposed   — customer_name and address absent from output
  3. Revenue calc      — rolling_30d_revenue correctly accumulates
  4. VIP threshold     — is_vip_customer triggers at threshold from metadata
  5. Quality gate      — validate_output() raises on bad data

Config is passed explicitly to each function, mirroring what run_pipeline()
does. Tests construct minimal config dicts — no dependency on metadata.yaml
file being present at test time.
"""

import pandas as pd
import pytest
from datetime import date

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline import (
    aggregate_daily_summary,
    calculate_metrics,
    get_output_config,
    load_metadata,
    mask_pii,
    validate_output,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_orders(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def minimal_config(vip_threshold: float = 5000.0) -> dict:
    """
    Minimal config dict that mirrors what get_output_config() returns.
    Tests use this instead of loading metadata.yaml so they remain fast
    and isolated from filesystem state.
    """
    return {
        "grain_keys": ["date", "customer_id"],
        "pii_fields": {"customer_name", "address", "email"},
        "output_columns": [
            "date", "customer_id", "daily_revenue",
            "rolling_30d_revenue", "stock_status", "is_vip_customer",
        ],
        "vip_threshold": vip_threshold,
    }


def minimal_meta(checks: list[dict] | None = None) -> dict:
    """Minimal metadata dict for validate_output() calls."""
    if checks is None:
        checks = [
            {"name": "grain_consistency"},
            {"name": "no_nulls_in_grain_keys"},
            {"name": "daily_revenue_non_negative"},
        ]
    return {"governance": {"data_quality": {"checks": checks}}}


# ---------------------------------------------------------------------------
# 1. Grain consistency
# ---------------------------------------------------------------------------

class TestGrainConsistency:
    """Output must contain exactly one row per (date, customer_id)."""

    def test_two_orders_same_customer_same_day_produce_one_row(self):
        orders = make_orders([
            {"customer_id": "C1", "product_id": "P1", "amount": 100.0,
             "timestamp": "2024-01-15 09:00", "payment_method": "card",
             "stock_status": "in_stock"},
            {"customer_id": "C1", "product_id": "P2", "amount": 200.0,
             "timestamp": "2024-01-15 14:00", "payment_method": "card",
             "stock_status": "in_stock"},
        ])
        orders = calculate_metrics(orders)
        summary = aggregate_daily_summary(orders, minimal_config())

        rows_for_c1 = summary[summary["customer_id"] == "C1"]
        assert len(rows_for_c1) == 1, (
            f"Expected 1 row for C1 on 2024-01-15, got {len(rows_for_c1)}. "
            "Grain violation — field may have been added at order level."
        )

    def test_two_customers_same_day_produce_two_rows(self):
        orders = make_orders([
            {"customer_id": "C1", "product_id": "P1", "amount": 100.0,
             "timestamp": "2024-01-15 09:00", "payment_method": "card",
             "stock_status": "in_stock"},
            {"customer_id": "C2", "product_id": "P2", "amount": 200.0,
             "timestamp": "2024-01-15 11:00", "payment_method": "card",
             "stock_status": "in_stock"},
        ])
        orders = calculate_metrics(orders)
        summary = aggregate_daily_summary(orders, minimal_config())

        assert len(summary) == 2

    def test_same_customer_different_days_produce_separate_rows(self):
        orders = make_orders([
            {"customer_id": "C1", "product_id": "P1", "amount": 100.0,
             "timestamp": "2024-01-15 09:00", "payment_method": "card",
             "stock_status": "in_stock"},
            {"customer_id": "C1", "product_id": "P1", "amount": 150.0,
             "timestamp": "2024-01-16 09:00", "payment_method": "card",
             "stock_status": "in_stock"},
        ])
        orders = calculate_metrics(orders)
        summary = aggregate_daily_summary(orders, minimal_config())

        assert len(summary) == 2


# ---------------------------------------------------------------------------
# 2. PII not exposed — driven by config["pii_fields"]
# ---------------------------------------------------------------------------

class TestPIINotExposed:
    """Fields in config['pii_fields'] must not appear in output columns."""

    def test_customer_name_not_in_output_columns(self):
        orders = make_orders([
            {"customer_id": "C1", "product_id": "P1", "amount": 100.0,
             "timestamp": "2024-01-15 09:00", "payment_method": "card",
             "stock_status": "in_stock", "customer_name": "Jane Doe",
             "address": "123 Main St"},
        ])
        orders = calculate_metrics(orders)
        summary = aggregate_daily_summary(orders, minimal_config())

        assert "customer_name" not in summary.columns, (
            "PII LEAK: customer_name in output. "
            "Should be excluded via config['output_columns'] derived from metadata.yaml."
        )

    def test_address_not_in_output_columns(self):
        orders = make_orders([
            {"customer_id": "C1", "product_id": "P1", "amount": 100.0,
             "timestamp": "2024-01-15 09:00", "payment_method": "card",
             "stock_status": "in_stock", "customer_name": "Jane Doe",
             "address": "123 Main St"},
        ])
        orders = calculate_metrics(orders)
        summary = aggregate_daily_summary(orders, minimal_config())

        assert "address" not in summary.columns

    def test_output_columns_match_config(self):
        """output_columns in config fully determines what's written — nothing more, nothing less."""
        orders = make_orders([
            {"customer_id": "C1", "product_id": "P1", "amount": 100.0,
             "timestamp": "2024-01-15 09:00", "payment_method": "card",
             "stock_status": "in_stock"},
        ])
        orders = calculate_metrics(orders)
        config = minimal_config()
        summary = aggregate_daily_summary(orders, config)

        assert list(summary.columns) == config["output_columns"]


# ---------------------------------------------------------------------------
# 3. Revenue calculation correctness
# ---------------------------------------------------------------------------

class TestRevenueCalculation:

    def test_daily_revenue_sums_all_orders_for_customer_day(self):
        orders = make_orders([
            {"customer_id": "C1", "product_id": "P1", "amount": 100.0,
             "timestamp": "2024-01-15 09:00", "payment_method": "card",
             "stock_status": "in_stock"},
            {"customer_id": "C1", "product_id": "P2", "amount": 250.0,
             "timestamp": "2024-01-15 16:00", "payment_method": "card",
             "stock_status": "in_stock"},
        ])
        orders = calculate_metrics(orders)
        summary = aggregate_daily_summary(orders, minimal_config())

        assert summary["daily_revenue"].iloc[0] == pytest.approx(350.0)

    def test_rolling_revenue_accumulates_across_days(self):
        orders = make_orders([
            {"customer_id": "C1", "product_id": "P1", "amount": 1000.0,
             "timestamp": "2024-01-14 09:00", "payment_method": "card",
             "stock_status": "in_stock"},
            {"customer_id": "C1", "product_id": "P1", "amount": 2000.0,
             "timestamp": "2024-01-15 09:00", "payment_method": "card",
             "stock_status": "in_stock"},
        ])
        orders = calculate_metrics(orders)
        summary = aggregate_daily_summary(orders, minimal_config()).sort_values("date")

        assert summary.iloc[1]["rolling_30d_revenue"] >= 3000.0


# ---------------------------------------------------------------------------
# 4. VIP threshold — read from config, not hardcoded
# ---------------------------------------------------------------------------

class TestVIPCustomerFlag:
    """
    VIP threshold comes from config['vip_threshold'] which is read from
    metadata.yaml at runtime. These tests pass threshold explicitly to
    confirm the pipeline respects whatever value metadata declares.
    """

    def test_customer_below_threshold_is_not_vip(self):
        orders = make_orders([
            {"customer_id": "C1", "product_id": "P1", "amount": 4999.99,
             "timestamp": "2024-01-15 09:00", "payment_method": "card",
             "stock_status": "in_stock"},
        ])
        orders = calculate_metrics(orders)
        summary = aggregate_daily_summary(orders, minimal_config(vip_threshold=5000.0))

        assert summary["is_vip_customer"].iloc[0] == False

    def test_customer_at_threshold_is_vip(self):
        orders = make_orders([
            {"customer_id": "C1", "product_id": "P1", "amount": 5000.00,
             "timestamp": "2024-01-15 09:00", "payment_method": "card",
             "stock_status": "in_stock"},
        ])
        orders = calculate_metrics(orders)
        summary = aggregate_daily_summary(orders, minimal_config(vip_threshold=5000.0))

        assert summary["is_vip_customer"].iloc[0] == True

    def test_threshold_is_configurable(self):
        """Changing threshold in metadata changes VIP behavior — no code change required."""
        orders = make_orders([
            {"customer_id": "C1", "product_id": "P1", "amount": 3000.0,
             "timestamp": "2024-01-15 09:00", "payment_method": "card",
             "stock_status": "in_stock"},
        ])
        orders = calculate_metrics(orders)

        # At default $5000 threshold — not VIP
        summary = aggregate_daily_summary(orders, minimal_config(vip_threshold=5000.0))
        assert summary["is_vip_customer"].iloc[0] == False

        # Lower threshold in metadata → becomes VIP without touching Python
        summary = aggregate_daily_summary(orders, minimal_config(vip_threshold=2500.0))
        assert summary["is_vip_customer"].iloc[0] == True

    def test_vip_evaluated_at_customer_day_grain_not_order_level(self):
        """VIP must reflect combined 30-day revenue, not any single order."""
        orders = make_orders([
            {"customer_id": "C1", "product_id": "P1", "amount": 3000.00,
             "timestamp": "2024-01-15 09:00", "payment_method": "card",
             "stock_status": "in_stock"},
            {"customer_id": "C1", "product_id": "P2", "amount": 2500.00,
             "timestamp": "2024-01-15 14:00", "payment_method": "card",
             "stock_status": "in_stock"},
        ])
        orders = calculate_metrics(orders)
        summary = aggregate_daily_summary(orders, minimal_config())

        assert summary["is_vip_customer"].iloc[0] == True, (
            "VIP flag should be True when combined revenue >= threshold, "
            "even if no single order exceeds it."
        )


# ---------------------------------------------------------------------------
# 5. validate_output — checks driven by metadata
# ---------------------------------------------------------------------------

class TestValidateOutput:
    """
    validate_output runs the checks declared in metadata.yaml.
    Tests confirm each named check is enforced and that adding/removing
    checks from metadata changes what gets validated.
    """

    def _good_summary(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "date": date(2024, 1, 15),
            "customer_id": "C1",
            "daily_revenue": 100.0,
            "rolling_30d_revenue": 100.0,
            "stock_status": "in_stock",
            "is_vip_customer": False,
        }])

    def test_valid_data_passes_all_checks(self):
        validate_output(self._good_summary(), minimal_meta(), minimal_config())

    def test_grain_consistency_check_catches_duplicates(self):
        df = pd.concat([self._good_summary(), self._good_summary()], ignore_index=True)
        with pytest.raises(ValueError, match="Grain violation"):
            validate_output(df, minimal_meta(), minimal_config())

    def test_no_nulls_check_catches_null_customer_id(self):
        df = self._good_summary()
        df["customer_id"] = None
        with pytest.raises(ValueError, match="grain key 'customer_id'"):
            validate_output(df, minimal_meta(), minimal_config())

    def test_revenue_check_catches_negative_values(self):
        df = self._good_summary()
        df["daily_revenue"] = -1.0
        with pytest.raises(ValueError, match="negative daily_revenue"):
            validate_output(df, minimal_meta(), minimal_config())

    def test_disabling_a_check_in_metadata_skips_it(self):
        """If a check is removed from metadata, validate_output skips it."""
        df = pd.concat([self._good_summary(), self._good_summary()], ignore_index=True)
        # Remove grain_consistency from checks — duplicate rows should pass now
        meta_without_grain_check = minimal_meta(checks=[
            {"name": "no_nulls_in_grain_keys"},
            {"name": "daily_revenue_non_negative"},
        ])
        # Should not raise — grain check was removed from metadata
        validate_output(df, meta_without_grain_check, minimal_config())


# ---------------------------------------------------------------------------
# 6. get_output_config — reads real metadata.yaml
# ---------------------------------------------------------------------------

class TestGetOutputConfig:
    """
    Integration: confirms get_output_config() correctly parses metadata.yaml.
    This is the bridge between the YAML contract and runtime behavior.
    """

    def test_output_columns_exclude_pii_fields(self):
        meta = load_metadata()
        config = get_output_config(meta)

        for pii_field in config["pii_fields"]:
            assert pii_field not in config["output_columns"], (
                f"PII field '{pii_field}' found in output_columns. "
                "metadata.yaml governance.pii_rules.never_expose_in_outputs must be respected."
            )

    def test_grain_keys_from_metadata(self):
        meta = load_metadata()
        config = get_output_config(meta)

        assert config["grain_keys"] == ["date", "customer_id"]

    def test_vip_threshold_from_metadata(self):
        meta = load_metadata()
        config = get_output_config(meta)

        assert config["vip_threshold"] == 5000.0


# ---------------------------------------------------------------------------
# 7. PII masking helper
# ---------------------------------------------------------------------------

class TestMaskPII:

    def test_same_input_produces_same_hash(self):
        assert mask_pii("Jane Doe") == mask_pii("Jane Doe")

    def test_different_inputs_produce_different_hashes(self):
        assert mask_pii("Jane Doe") != mask_pii("John Smith")

    def test_none_returns_none(self):
        assert mask_pii(None) is None

    def test_hash_not_equal_to_original(self):
        assert mask_pii("Jane Doe") != "Jane Doe"
