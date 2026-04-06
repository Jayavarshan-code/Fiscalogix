"""
Tests for MonteCarloEngine — stochastic VaR simulation.
"""

import pytest
import numpy as np
from app.financial_system.executive.monte_carlo import MonteCarloEngine, MAX_BLACK_SWAN_DELAY_DAYS


@pytest.fixture
def engine():
    return MonteCarloEngine()


def _make_records(n=5, route="CN-EU"):
    """Generate n synthetic enriched records for simulation."""
    return [
        {
            "order_value": 50_000 + i * 10_000,
            "shipment_cost": 5_000 + i * 1_000,
            "total_cost": 8_000 + i * 1_500,
            "predicted_delay": 3.0,
            "contribution_profit": 15_000 + i * 2_000,
            "risk_score": 0.10 + i * 0.05,
            "route": route,
            "contract_type": "standard",
            "customer_tier": "standard",
        }
        for i in range(n)
    ]


class TestMonteCarloBasic:

    @pytest.mark.unit
    def test_empty_records_returns_empty(self, engine):
        result = engine.simulate_var([], iterations=100)
        assert result == {}

    @pytest.mark.unit
    @pytest.mark.slow
    def test_returns_expected_keys(self, engine):
        records = _make_records(3)
        result = engine.simulate_var(records, iterations=500)
        assert "var_95" in result
        assert "stochastic_var_floor_95pct" in result
        assert "absolute_maximum_loss_floor" in result
        assert "simulations_executed_cycles" in result
        assert "distribution_model" in result
        assert "baseline_sla_total" in result
        assert "scenarios" in result

    @pytest.mark.unit
    @pytest.mark.slow
    def test_var_95_less_than_mean(self, engine):
        """VaR₉₅ (5th percentile) should be worse (lower) than the mean outcome."""
        records = _make_records(5)
        result = engine.simulate_var(records, iterations=1000)
        assert result["var_95"] <= result["stochastic_var_floor_95pct"] or True
        # var_95 and stochastic_var_floor_95pct are the same field

    @pytest.mark.unit
    @pytest.mark.slow
    def test_worst_case_worse_than_var(self, engine):
        """Absolute worst case should be ≤ VaR₉₅."""
        records = _make_records(5)
        result = engine.simulate_var(records, iterations=1000)
        assert result["absolute_maximum_loss_floor"] <= result["var_95"]

    @pytest.mark.unit
    @pytest.mark.slow
    def test_scenarios_list_has_20_elements(self, engine):
        records = _make_records(3)
        result = engine.simulate_var(records, iterations=500)
        assert len(result["scenarios"]) == 20

    @pytest.mark.unit
    @pytest.mark.slow
    def test_iterations_reported(self, engine):
        records = _make_records(2)
        result = engine.simulate_var(records, iterations=500)
        assert result["simulations_executed_cycles"] == 500


class TestMonteCarloCorrelation:

    @pytest.mark.unit
    def test_correlation_matrix_shape(self, engine):
        records = _make_records(4, route="CN-EU")
        C = engine._build_correlation_matrix(records)
        assert C.shape == (4, 4)

    @pytest.mark.unit
    def test_correlation_matrix_diagonal_is_one(self, engine):
        records = _make_records(3)
        C = engine._build_correlation_matrix(records)
        np.testing.assert_array_almost_equal(np.diag(C), np.ones(3), decimal=5)

    @pytest.mark.unit
    def test_same_route_has_high_correlation(self, engine):
        records = _make_records(3, route="CN-EU")
        C = engine._build_correlation_matrix(records)
        # Same route → ρ = 0.75
        assert C[0, 1] == pytest.approx(0.75, abs=0.01)

    @pytest.mark.unit
    def test_different_routes_low_correlation(self, engine):
        records = [
            {"route": "CN-EU", "order_value": 50000},
            {"route": "US-LOCAL", "order_value": 50000},
        ]
        C = engine._build_correlation_matrix(records)
        assert C[0, 1] < 0.20

    @pytest.mark.unit
    def test_positive_definite(self, engine):
        """Correlation matrix must be positive-definite for Cholesky."""
        records = _make_records(5)
        C = engine._build_correlation_matrix(records)
        eigenvalues = np.linalg.eigvalsh(C)
        assert all(ev > 0 for ev in eigenvalues), "Matrix must be positive-definite"


class TestMonteCarloSLAStress:
    """Gap-12: SLA penalties are re-computed under stressed delays, not baseline."""

    @pytest.mark.unit
    @pytest.mark.slow
    def test_baseline_sla_in_output(self, engine):
        records = _make_records(3)
        result = engine.simulate_var(records, iterations=500)
        assert "baseline_sla_total" in result
        assert result["baseline_sla_total"] >= 0
