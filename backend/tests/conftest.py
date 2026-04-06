"""
Shared fixtures for the Fiscalogix test suite.

All unit tests run WITHOUT Redis, WITHOUT Postgres, WITHOUT ML model files.
We mock external dependencies at the module level BEFORE importing app code.
"""

import sys
import pytest
from unittest.mock import MagicMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# PRE-IMPORT MOCKING
# The redis_client module connects to Redis at import time (module-level
# `cache = get_redis_client()`). We must intercept this BEFORE any app
# module is imported, otherwise pytest hangs for 1s per test on a timeout.
# ─────────────────────────────────────────────────────────────────────────────

# Create a mock redis client that behaves like a no-op cache
_mock_cache = MagicMock()
_mock_cache.get.return_value = None
_mock_cache.setex.return_value = True
_mock_cache.set.return_value = True
_mock_cache.delete.return_value = True
_mock_cache.ping.return_value = True

# Create a mock redis_client module
_mock_redis_module = MagicMock()
_mock_redis_module.cache = _mock_cache
_mock_redis_module.get_redis_client = MagicMock(return_value=_mock_cache)

# Inject it into sys.modules BEFORE any app code imports redis_client
sys.modules["app.Db.redis_client"] = _mock_redis_module

# Also mock the admin register_model_status to prevent import side effects
_mock_admin = MagicMock()
_mock_admin.register_model_status = MagicMock()
_mock_admin.MODEL_HEALTH_REGISTRY = {}


# ─────────────────────────────────────────────────────────────────────────────
# Standard test row — represents a single enriched shipment record.
# Every financial model unit test uses this as the baseline input.
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def base_row():
    """A canonical enriched shipment row with all fields populated."""
    return {
        "order_id": "ORD-001",
        "shipment_id": "SHP-001",
        "tenant_id": "test_tenant",
        "customer_id": "CUST-100",
        "order_value": 100_000.0,
        "shipment_cost": 12_000.0,
        "total_cost": 15_000.0,
        "delay_days": 5,
        "predicted_delay": 5.0,
        "predicted_demand": 80_000.0,
        "credit_days": 30,
        "payment_delay_days": 5,
        "contribution_profit": 25_000.0,
        "carrier": "maersk",
        "route": "CN-EU",
        "cargo_type": "electronics",
        "customer_tier": "enterprise",
        "contract_type": "strict",
        "industry_vertical": "electronics",
        "order_month": 6,
        "wacc": 0.095,
        "risk_score": 0.12,
        "risk_confidence": 0.87,
        "revm": 18_000.0,
        "fx_cost": 500.0,
        "sla_penalty": 200.0,
        "time_cost": 300.0,
        "future_cost": 1_500.0,
    }


@pytest.fixture
def domestic_row(base_row):
    """A domestic shipment — no FX, no tariff, simple route."""
    row = base_row.copy()
    row.update({
        "route": "LOCAL",
        "carrier": "blue_dart",
        "order_value": 25_000.0,
        "shipment_cost": 3_000.0,
        "total_cost": 4_500.0,
        "credit_days": 0,
        "payment_delay_days": 0,
        "contribution_profit": 8_000.0,
        "cargo_type": "general_cargo",
        "customer_tier": "standard",
        "contract_type": "standard",
        "industry_vertical": "default",
    })
    return row


@pytest.fixture
def high_risk_row(base_row):
    """A shipment with very high risk indicators."""
    row = base_row.copy()
    row.update({
        "order_value": 500_000.0,
        "predicted_delay": 15.0,
        "delay_days": 15,
        "risk_score": 0.85,
        "customer_tier": "enterprise",
        "contract_type": "full_rejection",
        "contribution_profit": -20_000.0,
        "revm": -80_000.0,
    })
    return row


@pytest.fixture
def portfolio(base_row, domestic_row, high_risk_row):
    """A mixed portfolio of 3 shipments for aggregation tests."""
    return [base_row, domestic_row, high_risk_row]
