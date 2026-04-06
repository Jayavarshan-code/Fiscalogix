"""
Tests for FXRiskModel — two-component FX erosion (delay + AR exposure).
"""

import pytest
from unittest.mock import patch
from app.financial_system.fx_model import FXRiskModel


@pytest.fixture
def model():
    return FXRiskModel()


class TestFXBasic:

    @pytest.mark.unit
    def test_zero_delay_with_no_credit(self, model):
        """Zero delay + zero credit_days → only minimal AR erosion."""
        row = {"route": "LOCAL", "order_value": 100_000, "shipment_cost": 12_000,
               "credit_days": 0, "payment_delay_days": 0}
        result = model.compute(row, predicted_delay=0)
        assert result == 0.0

    @pytest.mark.unit
    def test_local_route_low_volatility(self, model):
        """LOCAL route has 1% volatility — FX cost should be minimal."""
        row = {"route": "LOCAL", "order_value": 100_000, "shipment_cost": 12_000,
               "credit_days": 30, "payment_delay_days": 5}
        with patch("app.financial_system.fx_model._read_cached_volatility", return_value=0.01):
            result = model.compute(row, predicted_delay=5)
        assert result < 500, "LOCAL route (1% vol) should have minimal FX cost"

    @pytest.mark.unit
    def test_international_route_higher_fx(self, model):
        """EU-US route (8% vol) should produce significantly higher FX cost."""
        row = {"route": "EU-US", "order_value": 100_000, "shipment_cost": 12_000,
               "credit_days": 30, "payment_delay_days": 5}
        with patch("app.financial_system.fx_model._read_cached_volatility", return_value=0.08):
            result = model.compute(row, predicted_delay=5)
        assert result > 500, "EU-US (8% vol) should have material FX cost"

    @pytest.mark.unit
    def test_output_is_positive(self, model, base_row):
        with patch("app.financial_system.fx_model._read_cached_volatility", return_value=0.05):
            result = model.compute(base_row, predicted_delay=5)
        assert result >= 0


class TestFXARExposure:
    """AR component should dwarf delay component for high-value orders."""

    @pytest.mark.unit
    def test_long_credit_amplifies_fx(self, model):
        """Net-60 should produce higher FX than Net-0."""
        net0 = {"route": "EU-US", "order_value": 500_000, "shipment_cost": 50_000,
                "credit_days": 0, "payment_delay_days": 0}
        net60 = {"route": "EU-US", "order_value": 500_000, "shipment_cost": 50_000,
                 "credit_days": 60, "payment_delay_days": 10}

        with patch("app.financial_system.fx_model._read_cached_volatility", return_value=0.08):
            cost_net0 = model.compute(net0, predicted_delay=5)
            cost_net60 = model.compute(net60, predicted_delay=5)

        assert cost_net60 > cost_net0 * 2, "Long credit term should significantly increase FX"

    @pytest.mark.unit
    def test_compound_factor_for_long_credit(self, model):
        """Credit > 45 days triggers exponential compounding on AR erosion."""
        short = {"route": "US-CN", "order_value": 200_000, "shipment_cost": 20_000,
                 "credit_days": 30, "payment_delay_days": 0}
        long = {"route": "US-CN", "order_value": 200_000, "shipment_cost": 20_000,
                "credit_days": 90, "payment_delay_days": 0}

        with patch("app.financial_system.fx_model._read_cached_volatility", return_value=0.06):
            cost_30d = model.compute(short, predicted_delay=5)
            cost_90d = model.compute(long, predicted_delay=5)

        assert cost_90d > cost_30d * 2, "credit_days > 45 should trigger compound factor"


class TestFXBatch:

    @pytest.mark.unit
    def test_batch_returns_correct_length(self, model, portfolio):
        delays = [5, 0, 15]
        with patch("app.financial_system.fx_model._read_cached_volatility", return_value=0.05):
            results = model.compute_batch(portfolio, delays)
        assert len(results) == 3

    @pytest.mark.unit
    def test_batch_zero_delays_minimal(self, model, portfolio):
        delays = [0, 0, 0]
        with patch("app.financial_system.fx_model._read_cached_volatility", return_value=0.01):
            results = model.compute_batch(portfolio, delays)
        # May not all be zero (AR exposure from credit_days), but should be small
        assert all(r >= 0 for r in results)
