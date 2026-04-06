"""
Tests for TimeValueModel — capital opportunity cost + pipeline holding cost.

Golden test values are hand-calculated and pinned. Any change to the formula
that alters these outputs will break the test, which is exactly the point.
"""

import pytest
from app.financial_system.time_model import TimeValueModel


@pytest.fixture
def model():
    return TimeValueModel()


class TestTimeValueModelBasic:
    """Core formula: capital_cost + pipeline_cost."""

    @pytest.mark.unit
    def test_zero_delay_returns_zero(self, model, base_row):
        assert model.compute(base_row, predicted_delay=0) == 0.0

    @pytest.mark.unit
    def test_negative_delay_returns_zero(self, model, base_row):
        assert model.compute(base_row, predicted_delay=-3) == 0.0

    @pytest.mark.unit
    def test_positive_delay_returns_positive(self, model, base_row):
        result = model.compute(base_row, predicted_delay=5)
        assert result > 0, "time_cost must be positive for any delay > 0"

    @pytest.mark.unit
    def test_output_is_float(self, model, base_row):
        result = model.compute(base_row, predicted_delay=5)
        assert isinstance(result, float)

    @pytest.mark.unit
    def test_output_is_rounded_to_2dp(self, model, base_row):
        result = model.compute(base_row, predicted_delay=7)
        # Check it's rounded to at most 2 decimal places
        assert result == round(result, 2)


class TestTimeValueModelFormula:
    """Verify the mathematical formula components."""

    @pytest.mark.unit
    def test_capital_cost_component(self, model):
        """capital_cost = order_value × WACC × (delay / 365)"""
        row = {
            "order_value": 100_000,
            "wacc": 0.10,
            "shipment_cost": 0,
            "cargo_type": "general_cargo",
        }
        result = model.compute(row, predicted_delay=365)
        # At 365 days: capital_cost = 100000 × 0.10 × 1.0 = 10000
        # pipeline_cost = 0 (no shipment_cost, fallback = 100000 × 0.12 = 12000)
        #   holding_base=12000, rate=0.20, pipeline = 12000 × 0.20 × 1.0 = 2400
        expected = 10_000.0 + 2_400.0
        assert result == expected

    @pytest.mark.unit
    def test_holding_rate_varies_by_cargo_type(self, model):
        """Pharmaceutical cargo should have higher holding rate than textile."""
        pharma_row = {"order_value": 50000, "shipment_cost": 5000, "cargo_type": "pharmaceutical"}
        textile_row = {"order_value": 50000, "shipment_cost": 5000, "cargo_type": "textile"}
        delay = 10

        pharma_cost = model.compute(pharma_row, delay)
        textile_cost = model.compute(textile_row, delay)

        assert pharma_cost > textile_cost, "Pharma holding rate (0.45) > textile (0.12)"

    @pytest.mark.unit
    def test_missing_shipment_cost_uses_fallback(self, model):
        """When shipment_cost is 0, fallback = order_value × logistics_cost_ratio."""
        row = {"order_value": 100_000, "shipment_cost": 0, "cargo_type": "electronics"}
        result = model.compute(row, predicted_delay=10)
        assert result > 0, "Should use order_value × 0.08 (electronics ratio) as holding base"


class TestTimeValueModelScaling:
    """Verify monotonic scaling — more delay = more cost."""

    @pytest.mark.unit
    def test_cost_increases_with_delay(self, model, base_row):
        cost_5d = model.compute(base_row, predicted_delay=5)
        cost_10d = model.compute(base_row, predicted_delay=10)
        cost_30d = model.compute(base_row, predicted_delay=30)

        assert cost_5d < cost_10d < cost_30d, "time_cost must increase monotonically with delay"

    @pytest.mark.unit
    def test_cost_scales_with_order_value(self, model):
        small = {"order_value": 10_000, "shipment_cost": 1_200, "cargo_type": "general_cargo"}
        large = {"order_value": 1_000_000, "shipment_cost": 120_000, "cargo_type": "general_cargo"}

        small_cost = model.compute(small, predicted_delay=5)
        large_cost = model.compute(large, predicted_delay=5)

        assert large_cost > small_cost * 50, "100x order_value should produce >50x time_cost"
