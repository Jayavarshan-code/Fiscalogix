"""Tests for LiquidityScoreEngine."""
import pytest
from app.financial_system.executive.liquidity_engine import LiquidityScoreEngine

@pytest.fixture
def engine():
    return LiquidityScoreEngine()

class TestLiquidityBasic:
    @pytest.mark.unit
    def test_empty_returns_zero(self, engine):
        assert engine.compute(50000, [], [], []) == 0

    @pytest.mark.unit
    def test_returns_integer(self, engine):
        records = [{"total_cost": 10000, "revm": 5000}]
        timeline = [{"daily_net": 3000}]
        result = engine.compute(50000, timeline, [], records)
        assert isinstance(result, int)

    @pytest.mark.unit
    def test_score_0_to_100(self, engine):
        records = [{"total_cost": 10000, "revm": 5000}, {"total_cost": 8000, "revm": -2000}]
        timeline = [{"daily_net": 3000}, {"daily_net": -1000}, {"daily_net": 2000}]
        result = engine.compute(50000, timeline, [{"severity_score": 2}], records)
        assert 0 <= result <= 100

    @pytest.mark.unit
    def test_high_cash_improves_score(self, engine):
        records = [{"total_cost": 10000, "revm": 5000}]
        timeline = [{"daily_net": 1000}]
        low = engine.compute(5000, timeline, [], records)
        high = engine.compute(500000, timeline, [], records)
        assert high > low

    @pytest.mark.unit
    def test_shocks_reduce_score(self, engine):
        records = [{"total_cost": 10000, "revm": 5000}]
        timeline = [{"daily_net": 3000}]
        no_shock = engine.compute(50000, timeline, [], records)
        with_shock = engine.compute(50000, timeline, [{"severity_score": 50}], records)
        assert with_shock < no_shock
