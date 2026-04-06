"""
Tests for DecisionEngine — 5-tier severity taxonomy with magnitude-aware thresholds.

Covers: all 5 decision tiers, XAI driver generation, confidence adjustment,
dynamic risk threshold scaling, and edge cases.
"""

import pytest
from app.financial_system.decision_engine import DecisionEngine


@pytest.fixture
def engine():
    return DecisionEngine()


class TestDecisionTiers:
    """Verify each of the 5 severity tiers triggers correctly."""

    @pytest.mark.unit
    def test_approve_execution(self, engine):
        row = {"revm": 5_000, "risk_score": 0.05, "risk_confidence": 0.90,
               "order_value": 50_000, "contribution_profit": 10_000,
               "time_cost": 100, "future_cost": 200, "predicted_delay": 1}
        result = engine.compute(row)
        assert result["action"] == "APPROVE EXECUTION"
        assert result["tier"] == 1

    @pytest.mark.unit
    def test_monitor_closely(self, engine):
        row = {"revm": 1_000, "risk_score": 0.55, "risk_confidence": 0.80,
               "order_value": 50_000, "contribution_profit": 10_000,
               "time_cost": 100, "future_cost": 200, "predicted_delay": 4}
        result = engine.compute(row)
        assert result["action"] == "MONITOR CLOSELY"
        assert result["tier"] == 2

    @pytest.mark.unit
    def test_escalate_to_management(self, engine):
        """ReVM between -2% and -10% of order_value → ESCALATE."""
        row = {"revm": -3_000, "risk_score": 0.40, "risk_confidence": 0.75,
               "order_value": 100_000, "contribution_profit": 10_000,
               "time_cost": 5_000, "future_cost": 3_000, "predicted_delay": 5}
        result = engine.compute(row)
        assert result["action"] == "ESCALATE TO MANAGEMENT"
        assert result["tier"] == 3

    @pytest.mark.unit
    def test_intervene_immediately(self, engine):
        """ReVM between -10% and -25% of order_value → INTERVENE."""
        row = {"revm": -15_000, "risk_score": 0.60, "risk_confidence": 0.70,
               "order_value": 100_000, "contribution_profit": 5_000,
               "time_cost": 8_000, "future_cost": 6_000, "predicted_delay": 10}
        result = engine.compute(row)
        assert result["action"] == "INTERVENE IMMEDIATELY"
        assert result["tier"] == 4

    @pytest.mark.unit
    def test_cancel_do_not_ship(self, engine):
        """ReVM < -25% of order_value → CANCEL."""
        row = {"revm": -50_000, "risk_score": 0.90, "risk_confidence": 0.65,
               "order_value": 100_000, "contribution_profit": -10_000,
               "time_cost": 20_000, "future_cost": 15_000, "predicted_delay": 20}
        result = engine.compute(row)
        assert result["action"] == "CANCEL / DO NOT SHIP"
        assert result["tier"] == 5


class TestDecisionReturnStructure:
    """Decision dict should have all required keys for frontend consumption."""

    @pytest.mark.unit
    def test_return_keys(self, engine, base_row):
        result = engine.compute(base_row)
        assert "action" in result
        assert "reason" in result
        assert "drivers" in result
        assert "confidence" in result
        assert "revm_pct" in result
        assert "tier" in result

    @pytest.mark.unit
    def test_drivers_is_list(self, engine, base_row):
        result = engine.compute(base_row)
        assert isinstance(result["drivers"], list)
        assert len(result["drivers"]) >= 1

    @pytest.mark.unit
    def test_tier_is_1_to_5(self, engine, base_row):
        result = engine.compute(base_row)
        assert 1 <= result["tier"] <= 5


class TestDecisionConfidence:
    """Confidence degrades for negative outcomes (model uncertainty increases)."""

    @pytest.mark.unit
    def test_positive_revm_preserves_confidence(self, engine):
        row = {"revm": 5_000, "risk_score": 0.10, "risk_confidence": 0.90,
               "order_value": 50_000, "contribution_profit": 10_000,
               "time_cost": 100, "future_cost": 100, "predicted_delay": 1}
        result = engine.compute(row)
        assert result["confidence"] == round(0.90 * 0.98, 2)

    @pytest.mark.unit
    def test_negative_revm_reduces_confidence(self, engine):
        row = {"revm": -50_000, "risk_score": 0.85, "risk_confidence": 0.90,
               "order_value": 100_000, "contribution_profit": -10_000,
               "time_cost": 20_000, "future_cost": 15_000, "predicted_delay": 20}
        result = engine.compute(row)
        assert result["confidence"] == round(0.90 * 0.88, 2)


class TestDecisionDynamicThreshold:
    """Large exposures should trigger earlier warning than small ones."""

    @pytest.mark.unit
    def test_large_exposure_lower_threshold(self, engine):
        """$500K order → threshold ~0.65. risk=0.70 should trigger escalation."""
        row = {"revm": 1_000, "risk_score": 0.70, "risk_confidence": 0.80,
               "order_value": 500_000, "contribution_profit": 50_000,
               "time_cost": 1_000, "future_cost": 500, "predicted_delay": 1}
        result = engine.compute(row)
        assert result["tier"] >= 3, "High exposure + high risk should escalate"

    @pytest.mark.unit
    def test_small_exposure_higher_threshold(self, engine):
        """$5K order → threshold ~0.79. risk=0.70 should NOT escalate."""
        row = {"revm": 500, "risk_score": 0.70, "risk_confidence": 0.80,
               "order_value": 5_000, "contribution_profit": 1_000,
               "time_cost": 50, "future_cost": 30, "predicted_delay": 1}
        result = engine.compute(row)
        assert result["tier"] <= 2, "Small exposure + moderate risk = monitor, not escalate"
