import math

class FutureImpactModel:
    """
    Calculates long-term financial damage from a delayed shipment using:
    1. Tiered Customer Lifetime Value (CLV) estimation by segment
    2. Weibull-esque churn probability curve (tolerance threshold model)

    WHY THIS WAS FLAWED:
    Previously, CLV was hardcoded as `predicted_demand * 5.0` for EVERY customer.
    This created two dangerous errors:
      - A spot buyer making a one-off $500 order gets CLV = $2,500 (wildly overstated).
        The system then recommends expensive air-freight upgrades to preserve a customer
        who will never order again.
      - A Tier-1 Enterprise client with $5M/year volume gets CLV = 5x their last order,
        ignoring that losing them costs $50M in lifetime revenue.
    This causes WRONG rerouting decisions in both directions.

    FIX: Customer-tier-aware CLV multipliers backed by segment lookup.
    Tier is read from the row (populated by ERP data during ingestion) and falls
    back to the conservative 'standard' multiplier for unknown segments.
    """

    # Multipliers represent how many future order cycles are at risk per delay event.
    # Based on B2B churn research (Bain & Co., Frederick Reichheld CLV frameworks).
    CLV_MULTIPLIER_BY_TIER = {
        "enterprise":    12.0,   # Multi-year contract, high switching cost
        "strategic":     8.0,    # Key account, 3-5 yr relationship
        "growth":        5.0,    # Growing mid-market, relationship in progress
        "standard":      3.0,    # Transactional but recurring
        "spot":          1.5,    # One-off; minimal future order expectation
        "trial":         1.0,    # New customer, unknown risk profile
    }

    def compute(self, row, predicted_delay, predicted_demand):
        # Determine CLV multiplier from customer segment
        customer_tier = str(row.get("customer_tier", "standard")).lower().strip()
        clv_multiplier = self.CLV_MULTIPLIER_BY_TIER.get(customer_tier, self.CLV_MULTIPLIER_BY_TIER["standard"])
        clv_at_risk = predicted_demand * clv_multiplier

        # ---------------------------------------------------------------
        # Behavioral Churn Model (Weibull-esque tolerance decay)
        # Customers absorb minor delays linearly, then churn exponentially
        # after patience threshold is breached.
        # ---------------------------------------------------------------
        tolerance_threshold = 3.0   # days before patience breaks

        if predicted_delay <= tolerance_threshold:
            # Low-risk linear zone: churn grows slowly
            churn_prob = 0.02 * (predicted_delay / tolerance_threshold)
        else:
            # Exponential decay of loyalty beyond threshold
            excess_delay = predicted_delay - tolerance_threshold
            churn_prob = 1.0 - math.exp(-0.25 * excess_delay)

        # Amplified brand damage: compromised margin signals product or process failure
        if row.get("contribution_profit", 0) < 0:
            churn_prob = min(churn_prob * 1.5, 1.0)

        future_loss_value = clv_at_risk * churn_prob
        return round(future_loss_value, 2)
