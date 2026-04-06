"""Tests for FinancialAggregator."""
import pytest
from app.financial_system.aggregator import FinancialAggregator

@pytest.fixture
def agg():
    return FinancialAggregator()

class TestAggregator:
    @pytest.mark.unit
    def test_correct_totals(self, agg):
        data = [
            {"order_value": 100000, "total_cost": 60000, "contribution_profit": 25000, "revm": 18000},
            {"order_value": 50000, "total_cost": 30000, "contribution_profit": 10000, "revm": -5000},
        ]
        s = agg.summarize(data)
        assert s["total_revenue"] == 150000
        assert s["total_cost"] == 90000
        assert s["total_profit"] == 35000
        assert s["total_revm"] == 13000
        assert s["loss_shipments"] == 1

    @pytest.mark.unit
    def test_no_losses(self, agg):
        data = [{"order_value": 50000, "total_cost": 30000, "contribution_profit": 15000, "revm": 10000}]
        s = agg.summarize(data)
        assert s["loss_shipments"] == 0

    @pytest.mark.unit
    def test_all_losses(self, agg):
        data = [
            {"order_value": 50000, "total_cost": 60000, "contribution_profit": -10000, "revm": -15000},
            {"order_value": 30000, "total_cost": 40000, "contribution_profit": -5000, "revm": -8000},
        ]
        s = agg.summarize(data)
        assert s["loss_shipments"] == 2
