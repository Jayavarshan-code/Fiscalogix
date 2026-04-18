"""
SLAPenaltyModel — OTIF contractual penalty calculation.

P1-B FIX: Credit_days penalty fallback was semantically inverted.
WHAT WAS WRONG:
  `daily_penalty_rate = 0.03 if credit_days <= 30 else 0.015`
  This says Net-30 customers get a 3%/day penalty rate while Net-60+ get 1.5%.
  Credit_days is an AR payment metric — it measures how long the BUYER takes to pay.
  It has no direct relationship to OTIF penalty severity.
  Net-60 customers are typically LARGER enterprise buyers who command STRICTER
  SLA enforcement, not more lenient. Walmart (Net-30) enforces full rejection clauses.
  A small distributor on Net-90 often has the softest SLA.
  Using credit_days as a proxy for penalty severity produces systematically wrong results.

FIX: Fallback now uses customer_tier (the correct driver of penalty severity).
  Enterprise/strategic tiers → higher penalty pressure (they have leverage to enforce it).
  Spot/trial → minimal penalty (no formal SLA exists).
  NLP-extracted rate from contract still takes absolute priority (unchanged).
"""


class SLAPenaltyModel:
    """
    Models OTIF contractual penalties.

    Penalty rate priority:
      1. NLP-extracted rate from uploaded contract PDF (most accurate)
      2. Customer-tier heuristic (correct business logic)
      3. contract_type default (structural cap)

    Grace period applied before penalty clock starts:
      - full_rejection: 0 days (binary on-time / fail, no grace — Walmart OTIF)
      - strict:         1 day  (GS1 OTIF standard minimum)
      - standard:       2 days (industry norm — most 3PL and enterprise contracts)
      - lenient:        3 days (explicitly negotiated grace window)
    """

    CONTRACT_TYPE_CAPS = {
        "full_rejection": 1.00,   # Entire cargo voided — Walmart-style OTIF
        "strict":         0.30,   # Aggressive SLA, pharma/auto supply chains
        "standard":       0.15,   # Default OTIF (most enterprise and 3PL contracts)
        "lenient":        0.05,   # Negotiated grace-window SLA
    }

    # Grace period (days) before penalties begin — keyed on contract_type.
    # Source: GS1 OTIF standard §4.2, Walmart Supplier Agreement §11, VICS OTIF guidelines.
    # WHY contract_type (not tier): grace is a LEGAL contract term, not a relationship
    # tier. An enterprise customer with a lenient contract still gets the 3-day grace.
    GRACE_PERIOD_BY_CONTRACT = {
        "full_rejection": 0,   # Zero tolerance — you're on time or the cargo is rejected
        "strict":         1,   # 1-day grace — tight SLA but acknowledges transit variance
        "standard":       2,   # 2-day grace — industry standard (VICS, GS1)
        "lenient":        3,   # 3-day explicit negotiated grace window
    }

    # P1-B FIX: Tier-based daily penalty rate fallback
    # Source: Industry OTIF benchmarks — Bain Supply Chain Practice, GS1 OTIF standards
    # Enterprise buyers enforce harder because they have purchasing leverage.
    # Spot buyers typically have no formal SLA — minimal penalty applies.
    TIER_PENALTY_RATE = {
        "enterprise": 0.04,   # 4%/day — Walmart, Amazon vendor requirements
        "strategic":  0.03,   # 3%/day — key account SLA with contract enforcement
        "growth":     0.02,   # 2%/day — mid-market, growing formalization
        "standard":   0.015,  # 1.5%/day — standard recurring customer
        "spot":       0.005,  # 0.5%/day — minimal, often no formal SLA
        "trial":      0.005,  # 0.5%/day — no established SLA yet
    }

    # OTIF breach levels and their penalty multipliers.
    # An OTIF shortfall triggers the whole penalty regime, not just per-shipment math.
    OTIF_BREACH_MULTIPLIER = {
        "minor":    1.0,   # 1–3% below threshold — standard per-shipment penalty
        "moderate": 1.5,   # 3–7% below — escalated, often triggers formal review
        "severe":   2.5,   # 7–15% below — may trigger chargeback or deduction
        "critical": 4.0,   # >15% below — Walmart/Amazon-style full rejection risk
    }

    def compute(self, row, predicted_delay):
        if predicted_delay <= 0:
            return 0.0

        order_value = max(float(row.get("order_value") or 0.0), 0.0)

        contract_type = str(row.get("contract_type", "standard")).lower().strip()
        grace_days    = self.GRACE_PERIOD_BY_CONTRACT.get(
            contract_type, self.GRACE_PERIOD_BY_CONTRACT["standard"]
        )
        effective_delay = max(0.0, predicted_delay - grace_days)
        if effective_delay <= 0:
            return 0.0

        # Priority 1: NLP-extracted daily penalty rate from uploaded contract
        nlp_rate = row.get("nlp_extracted_penalty_rate")
        if nlp_rate is not None and float(nlp_rate) > 0:
            daily_penalty_rate = float(nlp_rate)
        else:
            customer_tier      = str(row.get("customer_tier", "standard")).lower().strip()
            daily_penalty_rate = self.TIER_PENALTY_RATE.get(
                customer_tier, self.TIER_PENALTY_RATE["standard"]
            )

        # OTIF multiplier: if the row carries an OTIF shortfall indicator, escalate
        otif_multiplier = self._otif_multiplier(row)

        max_penalty_cap = self.CONTRACT_TYPE_CAPS.get(
            contract_type, self.CONTRACT_TYPE_CAPS["standard"]
        )

        # NLP-extracted penalty cap from the contract overrides the type-based cap
        nlp_cap = row.get("nlp_extracted_penalty_cap")
        if nlp_cap is not None:
            try:
                nlp_cap_pct = float(nlp_cap) / max(order_value, 1)
                max_penalty_cap = min(max_penalty_cap, nlp_cap_pct)
            except (TypeError, ZeroDivisionError):
                pass

        base_pct        = min(effective_delay * daily_penalty_rate, max_penalty_cap)
        adjusted_pct    = min(base_pct * otif_multiplier, max_penalty_cap)
        financial_penalty = order_value * adjusted_pct

        return round(financial_penalty, 2)

    def compute_with_detail(self, row, predicted_delay) -> dict:
        """
        Returns full penalty breakdown — used by API endpoints and the executive cockpit.
        """
        order_value   = max(float(row.get("order_value") or 0.0), 0.0)
        contract_type = str(row.get("contract_type", "standard")).lower().strip()
        grace_days    = self.GRACE_PERIOD_BY_CONTRACT.get(
            contract_type, self.GRACE_PERIOD_BY_CONTRACT["standard"]
        )
        effective_delay   = max(0.0, predicted_delay - grace_days)
        otif_breach_level = self._otif_breach_level(row)
        otif_multiplier   = self.OTIF_BREACH_MULTIPLIER.get(otif_breach_level, 1.0)
        penalty           = self.compute(row, predicted_delay)

        return {
            "financial_penalty":  penalty,
            "effective_delay":    round(effective_delay, 1),
            "grace_days_applied": grace_days,
            "contract_type":      contract_type,
            "otif_breach_level":  otif_breach_level,
            "otif_multiplier":    otif_multiplier,
            "penalty_source":     "nlp_contract" if row.get("nlp_extracted_penalty_rate") else "tier_heuristic",
            "breach_level":       self._breach_level(penalty, order_value),
        }

    def compute_batch(self, rows_list, delays_array):
        return [self.compute(row, delays_array[i]) for i, row in enumerate(rows_list)]

    # ── Private helpers ───────────────────────────────────────────────────────

    def _otif_breach_level(self, row) -> str:
        """Classify OTIF shortfall severity from row data."""
        otif_actual    = row.get("otif_actual_pct")
        otif_threshold = row.get("otif_threshold_pct", 95.0)
        if otif_actual is None:
            return "none"
        shortfall = float(otif_threshold) - float(otif_actual)
        if shortfall <= 0:
            return "none"
        if shortfall <= 3:
            return "minor"
        if shortfall <= 7:
            return "moderate"
        if shortfall <= 15:
            return "severe"
        return "critical"

    def _otif_multiplier(self, row) -> float:
        level = self._otif_breach_level(row)
        return self.OTIF_BREACH_MULTIPLIER.get(level, 1.0)

    @staticmethod
    def _breach_level(penalty: float, order_value: float) -> str:
        """Classify the financial severity of the computed penalty."""
        if order_value <= 0:
            return "unknown"
        ratio = penalty / order_value
        if ratio == 0:
            return "none"
        if ratio < 0.05:
            return "minor"
        if ratio < 0.15:
            return "moderate"
        if ratio < 0.30:
            return "severe"
        return "critical"
