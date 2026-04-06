"""
Tests for ConfidenceTrustEngine — model certainty × data completeness.
"""

import pytest
from app.financial_system.executive.confidence_engine import ConfidenceTrustEngine


@pytest.fixture
def engine():
    return ConfidenceTrustEngine()


class TestConfidenceBasic:

    @pytest.mark.unit
    def test_empty_records_returns_zero(self, engine):
        assert engine.compute([], []) == 0.0

    @pytest.mark.unit
    def test_returns_float_between_0_and_1(self, engine, portfolio):
        result = engine.compute(portfolio, [])
        assert 0.0 <= result <= 1.0

    @pytest.mark.unit
    def test_high_confidence_data_produces_high_score(self, engine):
        records = [
            {"risk_confidence": 0.95, "wacc": 0.08, "total_cost": 10_000,
             "predicted_demand": 50_000, "order_value": 100_000, "predicted_delay": 3},
            {"risk_confidence": 0.92, "wacc": 0.08, "total_cost": 8_000,
             "predicted_demand": 40_000, "order_value": 80_000, "predicted_delay": 2},
        ]
        result = engine.compute(records, [])
        assert result > 0.7

    @pytest.mark.unit
    def test_missing_data_reduces_score(self, engine):
        """Records missing critical fields should lower data completeness."""
        complete = [{"risk_confidence": 0.90, "wacc": 0.08, "total_cost": 10_000,
                     "predicted_demand": 50_000, "order_value": 100_000, "predicted_delay": 3}]
        incomplete = [{"risk_confidence": 0.90, "wacc": 0, "total_cost": 0,
                       "predicted_demand": 0, "order_value": 0, "predicted_delay": 3}]

        score_complete = engine.compute(complete, [])
        score_incomplete = engine.compute(incomplete, [])

        assert score_complete > score_incomplete


class TestConfidenceVolatility:
    """Volatility should be reported separately, NOT reduce confidence."""

    @pytest.mark.unit
    def test_volatility_alert_set_on_shocks(self, engine):
        records = [
            {"risk_confidence": 0.85, "wacc": 0.08, "total_cost": 10_000,
             "predicted_demand": 50_000, "order_value": 100_000, "predicted_delay": 2},
            {"risk_confidence": 0.85, "wacc": 0.08, "total_cost": 10_000,
             "predicted_demand": 50_000, "order_value": 100_000, "predicted_delay": 25},
        ]
        shocks = [{"severity_score": 5}]
        engine.compute(records, shocks)
        assert "volatility_alert" in shocks[0]
        assert shocks[0]["volatility_alert"] in ("NOMINAL", "MODERATE", "ELEVATED", "CRITICAL")

    @pytest.mark.unit
    def test_high_volatility_does_not_reduce_confidence(self, engine):
        """High delay variance should NOT penalize the confidence score."""
        stable = [
            {"risk_confidence": 0.90, "wacc": 0.08, "total_cost": 10_000,
             "predicted_demand": 50_000, "order_value": 100_000, "predicted_delay": 3},
            {"risk_confidence": 0.90, "wacc": 0.08, "total_cost": 10_000,
             "predicted_demand": 50_000, "order_value": 100_000, "predicted_delay": 4},
        ]
        volatile = [
            {"risk_confidence": 0.90, "wacc": 0.08, "total_cost": 10_000,
             "predicted_demand": 50_000, "order_value": 100_000, "predicted_delay": 1},
            {"risk_confidence": 0.90, "wacc": 0.08, "total_cost": 10_000,
             "predicted_demand": 50_000, "order_value": 100_000, "predicted_delay": 50},
        ]
        score_stable = engine.compute(stable, [])
        score_volatile = engine.compute(volatile, [])

        # Confidence should be the same or nearly the same — volatility is NOT a penalty
        assert abs(score_stable - score_volatile) < 0.05
