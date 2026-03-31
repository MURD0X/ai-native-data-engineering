"""
Tests for after/pipeline.py

Validates the five constraints that make this pipeline AI-safe:
  1. Grain consistency  — exactly one row per (date, customer_id)
  2. PII not exposed   — customer_name and address absent from output
  3. Revenue calc      — rolling_30d_revenue correctly accumulates
  4. VIP threshold     — is_vip_customer triggers at $5000
  5. Quality gate      — validate_output() raises on bad data
"""

import pandas as pd
import pytest
from datetime import date, datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline import (
    aggregate_daily_summary,
    calculate_metrics,
    mask_pii,
    validate_output,
    VIP_REVENUE_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_orders(rows: list[dict]) -> pd.DataFrame:
    """Construct a minimal order DataFrame for testing."""
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


# ---------------------------------------------------------------------------
# 1. Grain consistency
# ---------------------------------------------------------------------------

class TestGrainConsistency:
    """The output must contain exactly one row per (date, customer_id)."""

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
        summary = aggregate_daily_summary(orders)

        rows_for_c1 = summary[summary["customer_id"] == "C1"]
        assert len(rows_for_c1) == 1, (
            f"Expected 1 row for C1 on 2024-01-15, got {len(rows_for_c1)}. "
            "Grain violation — agent may have added field at order level."
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
        summary = aggregate_daily_summary(orders)

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
        summary = aggregate_daily_summary(orders)

        assert len(summary) == 2


# ---------------------------------------------------------------------------
# 2. PII not exposed in output
# ---------------------------------------------------------------------------

class TestPIINotExposed:
    """customer_name and address must never appear in the summary output."""

    def test_customer_name_not_in_output_columns(self):
        orders = make_orders([
            {"customer_id": "C1", "product_id": "P1", "amount": 100.0,
             "timestamp": "2024-01-15 09:00", "payment_method": "card",
             "stock_status": "in_stock", "customer_name": "Jane Doe",
             "address": "123 Main St"},
        ])
        orders = calculate_metrics(orders)
        summary = aggregate_daily_summary(orders)

        assert "customer_name" not in summary.columns, (
            "PII LEAK: customer_name found in output. "
            "Governance policy requires this field be excluded from daily_summary."
        )

    def test_address_not_in_output_columns(self):
        orders = make_orders([
            {"customer_id": "C1", "product_id": "P1", "amount": 100.0,
             "timestamp": "2024-01-15 09:00", "payment_method": "card",
             "stock_status": "in_stock", "customer_name": "Jane Doe",
             "address": "123 Main St"},
        ])
        orders = calculate_metrics(orders)
        summary = aggregate_daily_summary(orders)

        assert "address" not in summary.columns, (
            "PII LEAK: address found in output. "
            "Governance policy requires this field be excluded from daily_summary."
        )

    def test_payment_method_not_in_output_columns(self):
        orders = make_orders([
            {"customer_id": "C1", "product_id": "P1", "amount": 100.0,
             "timestamp": "2024-01-15 09:00", "payment_method": "credit_card",
             "stock_status": "in_stock"},
        ])
        orders = calculate_metrics(orders)
        summary = aggregate_daily_summary(orders)

        assert "payment_method" not in summary.columns


# ---------------------------------------------------------------------------
# 3. Revenue calculation correctness
# ---------------------------------------------------------------------------

class TestRevenueCalculation:
    """Daily revenue and rolling 30-day revenue must be correct."""

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
        summary = aggregate_daily_summary(orders)

        assert summary["daily_revenue"].iloc[0] == pytest.approx(350.0), (
            "Daily revenue should sum all orders for the customer on that day."
        )

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
        summary = aggregate_daily_summary(orders).sort_values("date")

        # Day 2 rolling revenue should include day 1's order
        day2 = summary.iloc[1]
        assert day2["rolling_30d_revenue"] >= 3000.0


# ---------------------------------------------------------------------------
# 4. VIP customer threshold
# ---------------------------------------------------------------------------

class TestVIPCustomerFlag:
    """is_vip_customer must be True iff rolling_30d_revenue >= $5000."""

    def test_customer_below_threshold_is_not_vip(self):
        orders = make_orders([
            {"customer_id": "C1", "product_id": "P1", "amount": 4999.99,
             "timestamp": "2024-01-15 09:00", "payment_method": "card",
             "stock_status": "in_stock"},
        ])
        orders = calculate_metrics(orders)
        summary = aggregate_daily_summary(orders)

        assert summary["is_vip_customer"].iloc[0] == False

    def test_customer_at_threshold_is_vip(self):
        orders = make_orders([
            {"customer_id": "C1", "product_id": "P1", "amount": 5000.00,
             "timestamp": "2024-01-15 09:00", "payment_method": "card",
             "stock_status": "in_stock"},
        ])
        orders = calculate_metrics(orders)
        summary = aggregate_daily_summary(orders)

        assert summary["is_vip_customer"].iloc[0] == True

    def test_customer_above_threshold_is_vip(self):
        orders = make_orders([
            {"customer_id": "C1", "product_id": "P1", "amount": 7500.00,
             "timestamp": "2024-01-15 09:00", "payment_method": "card",
             "stock_status": "in_stock"},
        ])
        orders = calculate_metrics(orders)
        summary = aggregate_daily_summary(orders)

        assert summary["is_vip_customer"].iloc[0] == True

    def test_vip_evaluated_at_customer_day_grain_not_order_level(self):
        """VIP status must reflect total 30-day revenue, not a single order."""
        # Two orders that each alone are below threshold, combined above it
        orders = make_orders([
            {"customer_id": "C1", "product_id": "P1", "amount": 3000.00,
             "timestamp": "2024-01-15 09:00", "payment_method": "card",
             "stock_status": "in_stock"},
            {"customer_id": "C1", "product_id": "P2", "amount": 2500.00,
             "timestamp": "2024-01-15 14:00", "payment_method": "card",
             "stock_status": "in_stock"},
        ])
        orders = calculate_metrics(orders)
        summary = aggregate_daily_summary(orders)

        assert summary["is_vip_customer"].iloc[0] == True, (
            "VIP flag should be True when combined 30-day revenue >= $5000, "
            "even if no single order exceeds the threshold."
        )


# ---------------------------------------------------------------------------
# 5. validate_output quality gate
# ---------------------------------------------------------------------------

class TestValidateOutput:
    """validate_output() must raise ValueError on bad data."""

    def _good_summary(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "date": date(2024, 1, 15),
            "customer_id": "C1",
            "daily_revenue": 100.0,
            "rolling_30d_revenue": 100.0,
            "stock_status": "in_stock",
            "is_vip_customer": False,
        }])

    def test_valid_data_passes(self):
        validate_output(self._good_summary())  # should not raise

    def test_duplicate_grain_keys_raises(self):
        df = pd.concat([self._good_summary(), self._good_summary()], ignore_index=True)
        with pytest.raises(ValueError, match="Grain violation"):
            validate_output(df)

    def test_null_customer_id_raises(self):
        df = self._good_summary()
        df["customer_id"] = None
        with pytest.raises(ValueError, match="grain key 'customer_id'"):
            validate_output(df)

    def test_negative_revenue_raises(self):
        df = self._good_summary()
        df["daily_revenue"] = -1.0
        with pytest.raises(ValueError, match="negative daily_revenue"):
            validate_output(df)


# ---------------------------------------------------------------------------
# 6. PII masking helper
# ---------------------------------------------------------------------------

class TestMaskPII:
    """mask_pii() must be consistent, irreversible, and handle None."""

    def test_same_input_produces_same_hash(self):
        assert mask_pii("Jane Doe") == mask_pii("Jane Doe")

    def test_different_inputs_produce_different_hashes(self):
        assert mask_pii("Jane Doe") != mask_pii("John Smith")

    def test_none_returns_none(self):
        assert mask_pii(None) is None

    def test_hash_not_equal_to_original(self):
        original = "Jane Doe"
        assert mask_pii(original) != original
