"""
Tests for TariffDutyModel — import duty and customs tariff cost.

Covers: domestic zero-tariff, route-based rates, HS code overrides,
duty drawback netting, and edge cases.
"""

import pytest
from unittest.mock import patch
from app.financial_system.tariff_model import TariffDutyModel


@pytest.fixture
def model():
    return TariffDutyModel()


class TestTariffBasic:

    @pytest.mark.unit
    def test_domestic_is_zero(self, model):
        row = {"route": "LOCAL", "order_value": 100_000}
        assert model.compute(row) == 0.0

    @pytest.mark.unit
    def test_hub_route_is_zero(self, model):
        row = {"route": "HUB_DELHI", "order_value": 100_000}
        assert model.compute(row) == 0.0

    @pytest.mark.unit
    def test_zero_order_value_is_zero(self, model):
        row = {"route": "US-CN", "order_value": 0}
        assert model.compute(row) == 0.0

    @pytest.mark.unit
    def test_cross_border_produces_tariff(self, model):
        row = {"route": "US-CN", "order_value": 100_000}
        result = model.compute(row)
        assert result > 0

    @pytest.mark.unit
    def test_output_is_rounded(self, model):
        row = {"route": "US-CN", "order_value": 123_456.78}
        result = model.compute(row)
        assert result == round(result, 2)


class TestTariffRates:
    """Verify rate resolution: HS code > route > default."""

    @pytest.mark.unit
    def test_us_cn_rate_is_22pct(self, model):
        """US-CN route tariff = 22%."""
        row = {"route": "US-CN", "order_value": 100_000}
        result = model.compute(row)
        assert result == 22_000.0

    @pytest.mark.unit
    def test_eu_us_rate_is_3_5pct(self, model):
        """EU-US route tariff = 3.5%."""
        row = {"route": "EU-US", "order_value": 100_000}
        result = model.compute(row)
        assert result == 3_500.0

    @pytest.mark.unit
    def test_hs_code_overrides_route(self, model):
        """HS chapter 85 (electronics) = 25%, overrides EU-US default of 3.5%."""
        row = {"route": "EU-US", "order_value": 100_000, "hs_code": "8542.31"}
        result = model.compute(row)
        assert result == 25_000.0, "HS code should override route-based rate"

    @pytest.mark.unit
    def test_pharma_zero_rated(self, model):
        """HS chapter 30 (pharmaceuticals) = 0% under WTO pharma agreement."""
        row = {"route": "US-CN", "order_value": 500_000, "hs_code": "3004.90"}
        result = model.compute(row)
        assert result == 0.0


class TestTariffDrawback:
    """Duty drawback reduces net tariff cost."""

    @pytest.mark.unit
    def test_drawback_reduces_tariff(self, model):
        """50% drawback → net tariff halved."""
        no_drawback = {"route": "US-CN", "order_value": 100_000}
        with_drawback = {"route": "US-CN", "order_value": 100_000, "duty_drawback_rate": 0.50}

        full_tariff = model.compute(no_drawback)
        reduced_tariff = model.compute(with_drawback)

        assert reduced_tariff == pytest.approx(full_tariff * 0.50, abs=1)

    @pytest.mark.unit
    def test_drawback_capped_at_99pct(self, model):
        """Drawback rate is clamped to 99% even if input is higher."""
        row = {"route": "US-CN", "order_value": 100_000, "duty_drawback_rate": 1.50}
        result = model.compute(row)
        # 22% tariff × (1 - 0.99) = 22000 × 0.01 = 220
        assert result == pytest.approx(220, abs=1)


class TestTariffBatch:

    @pytest.mark.unit
    def test_batch_returns_correct_length(self, model, portfolio):
        results = model.compute_batch(portfolio)
        assert len(results) == len(portfolio)
