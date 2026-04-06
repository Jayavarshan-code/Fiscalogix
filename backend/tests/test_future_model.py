"""
Tests for FutureImpactModel — CLV-at-risk × churn probability.

Covers: tier multipliers, tolerance thresholds, industry amplifiers,
CLV calibration injection (Gap-7), and dict return format.
"""

import pytest
from app.financial_system.future_model import FutureImpactModel


@pytest.fixture
def model():
    return FutureImpactModel()


class TestFutureBasic:

    @pytest.mark.unit
    def test_zero_delay_returns_zero(self, model, base_row):
        result = model.compute(base_row, predicted_delay=0, predicted_demand=50_000)
        # Returns dict now
        assert result["value"] == 0.0

    @pytest.mark.unit
    def test_negative_delay_returns_zero(self, model, base_row):
        result = model.compute(base_row, predicted_delay=-1, predicted_demand=50_000)
        assert result["value"] == 0.0

    @pytest.mark.unit
    def test_positive_delay_returns_positive(self, model, base_row):
        result = model.compute(base_row, predicted_delay=5, predicted_demand=50_000)
        assert result["value"] > 0

    @pytest.mark.unit
    def test_returns_dict_with_all_fields(self, model, base_row):
        result = model.compute(base_row, predicted_delay=5, predicted_demand=50_000)
        assert isinstance(result, dict)
        assert "value" in result
        assert "clv_multiplier" in result
        assert "clv_source" in result
        assert "churn_probability" in result
        assert "clv_at_risk" in result


class TestFutureTierMultipliers:

    @pytest.mark.unit
    def test_enterprise_higher_clv_than_spot(self, model):
        enterprise = {"customer_tier": "enterprise", "industry_vertical": "default"}
        spot = {"customer_tier": "spot", "industry_vertical": "default"}

        ent_result = model.compute(enterprise, 5, 50_000)
        spot_result = model.compute(spot, 5, 50_000)

        assert ent_result["value"] > spot_result["value"]
        assert ent_result["clv_multiplier"] > spot_result["clv_multiplier"]

    @pytest.mark.unit
    def test_unknown_tier_defaults_to_standard(self, model):
        row = {"customer_tier": "nonexistent_tier", "industry_vertical": "default"}
        result = model.compute(row, 5, 50_000)
        assert result["clv_multiplier"] == 3.0  # standard multiplier


class TestFutureToleranceThresholds:

    @pytest.mark.unit
    def test_below_tolerance_produces_mild_churn(self, model):
        """Enterprise tolerance = 1 day. 0.5-day delay is within tolerance."""
        row = {"customer_tier": "enterprise", "industry_vertical": "default"}
        result = model.compute(row, predicted_delay=0.5, predicted_demand=50_000)
        assert result["churn_probability"] < 0.05, "Sub-tolerance should have very low churn"

    @pytest.mark.unit
    def test_above_tolerance_produces_high_churn(self, model):
        """Enterprise tolerance = 1 day. 10-day delay is way beyond tolerance."""
        row = {"customer_tier": "enterprise", "industry_vertical": "default"}
        result = model.compute(row, predicted_delay=10, predicted_demand=50_000)
        assert result["churn_probability"] > 0.5, "10-day excess for enterprise should have high churn"


class TestFutureIndustryAmplifiers:

    @pytest.mark.unit
    def test_pharma_amplifies_churn(self, model):
        """Pharmaceutical delays carry 2x churn amplification."""
        pharma = {"customer_tier": "standard", "industry_vertical": "pharmaceutical"}
        generic = {"customer_tier": "standard", "industry_vertical": "default"}

        pharma_result = model.compute(pharma, 5, 50_000)
        generic_result = model.compute(generic, 5, 50_000)

        assert pharma_result["value"] > generic_result["value"]

    @pytest.mark.unit
    def test_fmcg_q4_seasonal_boost(self, model):
        """FMCG in Q4 (month 11) gets 1.5 × 1.2 = 1.8x industry amplification."""
        fmcg_q4 = {"customer_tier": "standard", "industry_vertical": "fmcg", "order_month": 11}
        fmcg_q2 = {"customer_tier": "standard", "industry_vertical": "fmcg", "order_month": 5}

        q4_result = model.compute(fmcg_q4, 5, 50_000)
        q2_result = model.compute(fmcg_q2, 5, 50_000)

        assert q4_result["value"] > q2_result["value"], "Q4 FMCG should have higher churn impact"


class TestFutureCLVCalibration:
    """Gap-7: calibrated CLV multipliers from shipment history."""

    @pytest.mark.unit
    def test_calibration_overrides_tier(self, model):
        """When clv_calibration is provided, its multiplier is used."""
        row = {"customer_tier": "spot", "industry_vertical": "default"}
        calibration = {"calibrated_multiplier": 8.0, "confidence": "full"}

        result = model.compute(row, 5, 50_000, clv_calibration=calibration)

        assert result["clv_multiplier"] == 8.0
        assert result["clv_source"] == "full"

    @pytest.mark.unit
    def test_no_calibration_uses_tier(self, model):
        """Without calibration, falls back to static tier multiplier."""
        row = {"customer_tier": "enterprise", "industry_vertical": "default"}

        result = model.compute(row, 5, 50_000, clv_calibration=None)

        assert result["clv_multiplier"] == 12.0
        assert result["clv_source"] == "tier_static"

    @pytest.mark.unit
    def test_churn_probability_capped_at_1(self, model):
        """Churn probability can never exceed 1.0, even with amplifiers stacked."""
        row = {
            "customer_tier": "enterprise",
            "industry_vertical": "pharmaceutical",
            "contribution_profit": -100_000,
        }
        result = model.compute(row, predicted_delay=100, predicted_demand=50_000)
        assert result["churn_probability"] <= 1.0
