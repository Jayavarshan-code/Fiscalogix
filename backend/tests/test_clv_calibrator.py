"""Tests for CLVCalibrator."""
import pytest
from app.financial_system.clv_calibrator import CLVCalibrator

class TestCLVCalibrationMath:
    @pytest.mark.unit
    def test_no_history_returns_none(self):
        cal = CLVCalibrator()
        cal._cache = None
        result = cal._compute_calibration("CUST-1", "enterprise", [])
        assert result is None

    @pytest.mark.unit
    def test_full_confidence_with_enough_history(self):
        history = [{"order_value": 10000, "days_ago": d} for d in range(0, 365, 30)]
        cal = CLVCalibrator()
        cal._cache = None
        result = cal._compute_calibration("CUST-1", "enterprise", history)
        assert result is not None
        assert result["confidence"] == "full"
        assert result["calibrated_multiplier"] > 0

    @pytest.mark.unit
    def test_blended_with_few_orders(self):
        history = [{"order_value": 10000, "days_ago": 30}, {"order_value": 12000, "days_ago": 60}]
        cal = CLVCalibrator()
        cal._cache = None
        result = cal._compute_calibration("CUST-1", "standard", history)
        assert result is not None
        assert result["confidence"] == "blended"

    @pytest.mark.unit
    def test_single_order_thin_blend(self):
        history = [{"order_value": 5000, "days_ago": 10}]
        cal = CLVCalibrator()
        cal._cache = None
        result = cal._compute_calibration("CUST-1", "spot", history)
        assert result is not None
        assert result["confidence"] == "blended_thin"

    @pytest.mark.unit
    def test_growth_signal_above_1_when_recent_higher(self):
        history = [
            {"order_value": 5000, "days_ago": 400},
            {"order_value": 5000, "days_ago": 500},
            {"order_value": 15000, "days_ago": 30},
            {"order_value": 15000, "days_ago": 60},
            {"order_value": 15000, "days_ago": 90},
        ]
        cal = CLVCalibrator()
        cal._cache = None
        result = cal._compute_calibration("CUST-1", "standard", history)
        assert result["growth_signal"] > 1.0

    @pytest.mark.unit
    def test_multiplier_clamped(self):
        cal = CLVCalibrator()
        cal._cache = None
        # Extreme history that would push multiplier very high
        history = [{"order_value": 100000, "days_ago": d} for d in range(0, 365, 7)]
        result = cal._compute_calibration("CUST-1", "enterprise", history)
        assert result["calibrated_multiplier"] <= 20.0
        assert result["calibrated_multiplier"] >= 0.5
