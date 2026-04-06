"""
FutureImpactModel — CLV-at-risk × churn probability.

P1-A FIX: Tolerance threshold was hardcoded at 3.0 days for ALL customer tiers.
WHAT WAS WRONG:
  Enterprise customers have contractual SLAs of 0-1 days (Walmart OTIF = same-day).
  Spot buyers often accept 5-7 days variance with no relationship damage.
  A hardcoded 3.0 applied the exponential churn decay at the same delay point
  regardless of tier — understating enterprise churn risk and overstating spot risk.
  This caused the system to under-prioritize enterprise shipments.

FIX: Tier-aware tolerance thresholds. Enterprise hits exponential churn after 1 day;
  spot buyers don't enter exponential territory until day 5.

P1-B FIX: Industry vertical was entirely absent from the churn model.
WHAT WAS WRONG:
  A 2-day pharma delay can trigger FDA regulatory non-compliance → churn probability
  approaches 1.0 regardless of tier. FMCG during Q4 peak: same.
  The model treated pharmaceutical same as bulk_grain for churn purposes.

FIX: Industry vertical multiplier on churn probability, applied before CLV calculation.

Gap-7 FIX: Per-account CLV calibration from actual shipment history.
WHAT WAS WRONG:
  Static tier multipliers (enterprise=12x, spot=1.5x) ignore actual purchase behavior.
  A "spot" customer who reorders weekly is worth far more than 1.5x order_value.
  An "enterprise" label on a customer with 0 repeat orders in 18 months overstates CLV.

FIX: compute() now accepts an optional clv_calibration dict from CLVCalibrator.
  When calibration confidence is 'full' or 'blended', the calibrated_multiplier
  (derived from frequency_signal × growth_signal × base_tier_mult) replaces the
  static tier multiplier. Thin history ('blended_thin') is given 25% weight.
  The calibration source is included in the return dict for SHAP-style transparency.
"""

import math


class FutureImpactModel:
    """
    Calculates long-term financial damage from a delayed shipment.

    Formula: future_loss = CLV_at_risk × churn_probability × industry_amplifier
    """

    # CLV multipliers by customer tier
    # (unchanged — already correct from prior fix)
    CLV_MULTIPLIER_BY_TIER = {
        "enterprise": 12.0,
        "strategic":   8.0,
        "growth":      5.0,
        "standard":    3.0,
        "spot":        1.5,
        "trial":       1.0,
    }

    # P1-A FIX: Tier-aware tolerance thresholds (days before exponential churn begins)
    # Source: B2B SLA benchmarks — Gartner, Bain & Co. supply chain research
    TOLERANCE_THRESHOLD_BY_TIER = {
        "enterprise": 1.0,   # Walmart OTIF, pharma distributors — zero tolerance
        "strategic":  2.0,   # Key accounts — tight SLA, relationship buffer
        "growth":     3.0,   # Mid-market — moderate tolerance
        "standard":   4.0,   # Recurring transactional — can absorb minor delays
        "spot":       5.0,   # One-off — no SLA expectation, high delay tolerance
        "trial":      3.0,   # Unknown profile — use conservative middle
    }

    # P1-B FIX: Industry vertical churn amplifiers
    # Applied as a multiplier on the raw churn probability.
    # Values > 1.0 mean the industry punishes delays harder than average.
    INDUSTRY_CHURN_AMPLIFIER = {
        "pharmaceutical":  2.0,   # Regulatory non-compliance risk; alternate sourcing is standard
        "fmcg":            1.5,   # Shelf availability = lost sale = immediate churn in peak
        "automotive":      1.8,   # JIT lines stop — catastrophic downstream impact
        "electronics":     1.3,   # Consumer launch windows; delayed = lost slot
        "textile":         1.1,   # Seasonal, but runway exists
        "industrial":      1.2,   # CAPEX-cycle sensitivity
        "default":         1.0,   # No amplification — general cargo baseline
    }

    def compute(self, row, predicted_delay, predicted_demand, clv_calibration: dict = None):
        """
        Compute future revenue at risk from a delayed shipment.

        Gap-7: clv_calibration is a dict from CLVCalibrator.calibrate_batch().
        If provided, its calibrated_multiplier overrides the static tier benchmark.
        If None, the original tier multiplier is used (safe fallback).
        """
        customer_tier = str(row.get("customer_tier", "standard")).lower().strip()

        # ── Gap-7: use calibrated multiplier if available ─────────────────────
        static_multiplier = self.CLV_MULTIPLIER_BY_TIER.get(
            customer_tier, self.CLV_MULTIPLIER_BY_TIER["standard"]
        )
        if clv_calibration and "calibrated_multiplier" in clv_calibration:
            clv_multiplier = clv_calibration["calibrated_multiplier"]
            clv_source = clv_calibration.get("confidence", "calibrated")
        else:
            clv_multiplier = static_multiplier
            clv_source = "tier_static"

        clv_at_risk = predicted_demand * clv_multiplier

        # ── P1-A: Tier-aware tolerance threshold ─────────────────────────────
        tolerance = self.TOLERANCE_THRESHOLD_BY_TIER.get(
            customer_tier, self.TOLERANCE_THRESHOLD_BY_TIER["standard"]
        )

        if predicted_delay <= 0:
            return 0.0

        if predicted_delay <= tolerance:
            # Linear zone: churn grows slowly within SLA tolerance band
            churn_prob = 0.02 * (predicted_delay / tolerance)
        else:
            # Exponential decay beyond tolerance — loyalty erodes rapidly
            excess_delay = predicted_delay - tolerance
            # Decay rate steeper for enterprise (they switch faster with more options)
            decay_rates = {
                "enterprise": 0.50,
                "strategic":  0.35,
                "growth":     0.25,
                "standard":   0.20,
                "spot":       0.15,
                "trial":      0.20,
            }
            k = decay_rates.get(customer_tier, 0.25)
            churn_prob = 1.0 - math.exp(-k * excess_delay)

        # Negative margin amplifier: tier-weighted (enterprise loss is more visible)
        if row.get("contribution_profit", 0) < 0:
            tier_amplifiers = {
                "enterprise": 1.8,   # Brand/contract damage compounds
                "strategic":  1.6,
                "growth":     1.4,
                "standard":   1.3,
                "spot":       1.1,
                "trial":      1.1,
            }
            amp = tier_amplifiers.get(customer_tier, 1.3)
            churn_prob = min(churn_prob * amp, 1.0)

        # ── P1-B: Industry vertical amplifier ────────────────────────────────
        vertical = str(row.get("industry_vertical", "default")).lower().strip()
        industry_amp = self.INDUSTRY_CHURN_AMPLIFIER.get(
            vertical, self.INDUSTRY_CHURN_AMPLIFIER["default"]
        )
        # Seasonal amplifier: FMCG in Q4 (Oct-Dec) gets additional 20% churn pressure
        if vertical == "fmcg":
            month = row.get("order_month", 6)
            if month in (10, 11, 12):
                industry_amp *= 1.20

        churn_prob = min(churn_prob * industry_amp, 1.0)

        future_loss_value = clv_at_risk * churn_prob
        return {
            "value":            round(future_loss_value, 2),
            "clv_multiplier":   round(clv_multiplier, 3),
            "clv_source":       clv_source,
            "churn_probability": round(churn_prob, 4),
            "clv_at_risk":      round(clv_at_risk, 2),
        }
