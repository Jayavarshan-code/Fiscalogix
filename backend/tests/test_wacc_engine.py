"""
Tests for WACCEngine — 3-tier dynamic WACC resolution.

Tests run without Redis (mocked) to verify fallback paths.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.financial_system.wacc_engine import (
    WACCEngine, _DAMODARAN_WACC, _FALLBACK_WACC,
    _DAMODARAN_BASELINE_RFR, fetch_and_warm_wacc_cache,
)


class TestWACCResolve:
    """resolve() — 3-tier hierarchy tests."""

    @pytest.mark.unit
    def test_per_row_wacc_takes_priority(self):
        engine = WACCEngine()
        row = {"wacc": 0.12, "industry_vertical": "pharmaceutical"}
        result = engine.resolve(row)
        assert result == 0.12

    @pytest.mark.unit
    def test_per_row_wacc_converts_percentage(self):
        """If row["wacc"] > 1.0, it's treated as percentage."""
        engine = WACCEngine()
        row = {"wacc": 12.5, "industry_vertical": "default"}
        result = engine.resolve(row)
        assert result == 0.125

    @pytest.mark.unit
    def test_damodaran_fallback_for_electronics(self):
        """When no row wacc and no Redis, should use Damodaran benchmark."""
        engine = WACCEngine()
        engine._cache = None  # force no Redis
        row = {"industry_vertical": "electronics"}
        result = engine.resolve(row)
        # electronics = 0.095, no adjustment (no Redis)
        assert result == _DAMODARAN_WACC["electronics"]

    @pytest.mark.unit
    def test_unknown_vertical_uses_default(self):
        engine = WACCEngine()
        engine._cache = None
        row = {"industry_vertical": "interstellar_cargo"}
        result = engine.resolve(row)
        assert result == _DAMODARAN_WACC["default"]

    @pytest.mark.unit
    def test_wacc_clamped_to_range(self):
        """WACC should be in [1%, 50%] range."""
        engine = WACCEngine()
        row = {"wacc": 0.001}  # Too low — should clamp to 1%
        result = engine.resolve(row)
        assert result >= 0.01

    @pytest.mark.unit
    def test_negative_wacc_clamped(self):
        """Negative wacc in row → should be ignored (falls through to engine)."""
        engine = WACCEngine()
        engine._cache = None
        row = {"wacc": -0.05, "industry_vertical": "default"}
        result = engine.resolve(row)
        assert result > 0


class TestWACCResolveBatch:
    """resolve_batch() stamps wacc onto each row."""

    @pytest.mark.unit
    def test_batch_stamps_wacc(self):
        engine = WACCEngine()
        engine._cache = None
        rows = [
            {"industry_vertical": "pharmaceutical"},
            {"industry_vertical": "fmcg"},
            {"wacc": 0.14},
        ]
        engine.resolve_batch(rows)
        assert rows[0]["wacc"] == _DAMODARAN_WACC["pharmaceutical"]
        assert rows[1]["wacc"] == _DAMODARAN_WACC["fmcg"]
        assert rows[2]["wacc"] == 0.14

    @pytest.mark.unit
    def test_batch_returns_list(self):
        engine = WACCEngine()
        engine._cache = None
        rows = [{"industry_vertical": "default"}, {"industry_vertical": "electronics"}]
        result = engine.resolve_batch(rows)
        assert isinstance(result, list)
        assert len(result) == 2


class TestWACCTenantOverride:
    """Tenant Redis override tests."""

    @pytest.mark.unit
    def test_set_and_get_override(self):
        """Mock Redis to test the set/get cycle."""
        mock_cache = MagicMock()
        storage = {}

        def mock_setex(key, ttl, value):
            storage[key] = value

        def mock_get(key):
            return storage.get(key)

        mock_cache.setex = mock_setex
        mock_cache.get = mock_get

        engine = WACCEngine()
        engine._cache = mock_cache

        engine.set_tenant_override("acme_corp", 0.132)
        result = engine.resolve({"industry_vertical": "default"}, tenant_id="acme_corp")
        assert result == 0.132

    @pytest.mark.unit
    def test_clear_override_reverts_to_damodaran(self):
        mock_cache = MagicMock()
        storage = {}

        def mock_setex(key, ttl, value):
            storage[key] = value

        def mock_get(key):
            return storage.get(key)

        def mock_delete(key):
            storage.pop(key, None)

        mock_cache.setex = mock_setex
        mock_cache.get = mock_get
        mock_cache.delete = mock_delete

        engine = WACCEngine()
        engine._cache = mock_cache

        engine.set_tenant_override("acme_corp", 0.132)
        engine.clear_tenant_override("acme_corp")

        row = {"industry_vertical": "pharmaceutical"}
        result = engine.resolve(row, tenant_id="acme_corp")
        # Should fall through to Damodaran since override was cleared
        assert result == _DAMODARAN_WACC["pharmaceutical"]


class TestWACCDiagnostics:

    @pytest.mark.unit
    def test_get_current_rates_returns_all_verticals(self):
        engine = WACCEngine()
        engine._cache = None
        rates = engine.get_current_rates()
        for vertical in _DAMODARAN_WACC:
            assert vertical in rates["industry_rates"]
