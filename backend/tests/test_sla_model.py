"""
Tests for SLAPenaltyModel — OTIF contractual penalty calculation.

Tests cover: grace period logic, tier-based rates, contract type caps,
NLP-extracted rate priority, and edge cases.
"""

import pytest
from app.financial_system.sla_model import SLAPenaltyModel


@pytest.fixture
def model():
    return SLAPenaltyModel()


class TestSLABasic:
    """Core behaviour: zero delay = zero penalty, positive delay = positive penalty."""

    @pytest.mark.unit
    def test_zero_delay_returns_zero(self, model, base_row):
        assert model.compute(base_row, predicted_delay=0) == 0.0

    @pytest.mark.unit
    def test_negative_delay_returns_zero(self, model, base_row):
        assert model.compute(base_row, predicted_delay=-5) == 0.0

    @pytest.mark.unit
    def test_positive_delay_returns_positive(self, model, base_row):
        result = model.compute(base_row, predicted_delay=5)
        assert result > 0

    @pytest.mark.unit
    def test_output_is_rounded(self, model, base_row):
        result = model.compute(base_row, predicted_delay=7)
        assert result == round(result, 2)


class TestSLAGracePeriod:
    """Grace period tests — delays within grace should produce zero penalty."""

    @pytest.mark.unit
    def test_strict_contract_1day_grace(self, model):
        """Strict contracts have 1-day grace. 1-day delay = $0."""
        row = {"order_value": 100_000, "contract_type": "strict", "customer_tier": "enterprise"}
        assert model.compute(row, predicted_delay=1) == 0.0

    @pytest.mark.unit
    def test_strict_contract_2day_triggers(self, model):
        """Strict contracts: 2 days ⇒ 1 effective day ⇒ penalty kicks in."""
        row = {"order_value": 100_000, "contract_type": "strict", "customer_tier": "enterprise"}
        result = model.compute(row, predicted_delay=2)
        assert result > 0

    @pytest.mark.unit
    def test_standard_contract_2day_grace(self, model):
        """Standard contracts have 2-day grace. 2 days = $0."""
        row = {"order_value": 100_000, "contract_type": "standard", "customer_tier": "standard"}
        assert model.compute(row, predicted_delay=2) == 0.0

    @pytest.mark.unit
    def test_lenient_contract_3day_grace(self, model):
        """Lenient contracts have 3-day grace. 3 days = $0."""
        row = {"order_value": 100_000, "contract_type": "lenient", "customer_tier": "standard"}
        assert model.compute(row, predicted_delay=3) == 0.0

    @pytest.mark.unit
    def test_full_rejection_no_grace(self, model):
        """Full rejection has 0 grace — 1-day delay triggers penalty immediately."""
        row = {"order_value": 100_000, "contract_type": "full_rejection", "customer_tier": "enterprise"}
        result = model.compute(row, predicted_delay=1)
        assert result > 0


class TestSLATierRates:
    """Verify that higher tiers pay higher penalty rates."""

    @pytest.mark.unit
    def test_enterprise_higher_than_spot(self, model):
        enterprise = {"order_value": 100_000, "contract_type": "standard", "customer_tier": "enterprise"}
        spot = {"order_value": 100_000, "contract_type": "standard", "customer_tier": "spot"}
        delay = 10

        ent_penalty = model.compute(enterprise, delay)
        spot_penalty = model.compute(spot, delay)

        assert ent_penalty > spot_penalty, "Enterprise (4%/day) should pay more than spot (0.5%/day)"


class TestSLAContractCaps:
    """Contract type caps limit maximum penalty as % of order value."""

    @pytest.mark.unit
    def test_lenient_cap_at_5pct(self, model):
        """Lenient cap = 5% of order_value. Even 100-day delay can't exceed this."""
        row = {"order_value": 100_000, "contract_type": "lenient", "customer_tier": "enterprise"}
        result = model.compute(row, predicted_delay=100)
        max_cap = 100_000 * 0.05  # $5,000
        assert result <= max_cap + 0.01, f"Lenient penalty ${result} exceeded 5% cap ${max_cap}"

    @pytest.mark.unit
    def test_full_rejection_cap_at_100pct(self, model):
        """Full rejection can wipe out the entire order value."""
        row = {"order_value": 100_000, "contract_type": "full_rejection", "customer_tier": "enterprise"}
        result = model.compute(row, predicted_delay=100)
        assert result <= 100_000.01  # 100% cap


class TestSLANLPOverride:
    """NLP-extracted rate from contract PDF takes absolute priority."""

    @pytest.mark.unit
    def test_nlp_rate_overrides_tier(self, model):
        """When nlp_extracted_penalty_rate is present, it overrides the tier heuristic."""
        row = {
            "order_value": 100_000,
            "contract_type": "standard",
            "customer_tier": "spot",  # normally 0.5%/day
            "nlp_extracted_penalty_rate": 0.10,  # 10%/day from contract
        }
        result = model.compute(row, predicted_delay=5)
        # effective_delay = 5 - 2 (standard grace) = 3 days
        # penalty = min(3 × 0.10, 0.15) × 100_000 = min(0.30, 0.15) × 100_000 = $15,000
        expected = 15_000.0
        assert result == expected


class TestSLABatch:
    """Batch compute returns correct number of results."""

    @pytest.mark.unit
    def test_batch_length(self, model, portfolio):
        delays = [5, 0, 15]
        results = model.compute_batch(portfolio, delays)
        assert len(results) == len(portfolio)

    @pytest.mark.unit
    def test_batch_zero_delay_is_zero(self, model, portfolio):
        delays = [0, 0, 0]
        results = model.compute_batch(portfolio, delays)
        assert all(r == 0.0 for r in results)
