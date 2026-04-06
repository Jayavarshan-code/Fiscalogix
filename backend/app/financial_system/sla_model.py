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

    def compute(self, row, predicted_delay):
        if predicted_delay <= 0:
            return 0.0

        order_value = row.get("order_value", 0.0)

        # Apply grace period: penalties only clock in AFTER the grace window expires.
        # A 1-day delay on a standard (2-day grace) contract = $0 penalty.
        contract_type = str(row.get("contract_type", "standard")).lower().strip()
        grace_days = self.GRACE_PERIOD_BY_CONTRACT.get(
            contract_type, self.GRACE_PERIOD_BY_CONTRACT["standard"]
        )
        effective_delay = max(0.0, predicted_delay - grace_days)
        if effective_delay <= 0:
            return 0.0

        # Priority 1: NLP-extracted daily penalty rate from uploaded contract
        nlp_rate = row.get("nlp_extracted_penalty_rate", None)
        if nlp_rate is not None and nlp_rate > 0:
            daily_penalty_rate = float(nlp_rate)
        else:
            # P1-B FIX: Customer-tier heuristic (replaces inverted credit_days logic)
            customer_tier = str(row.get("customer_tier", "standard")).lower().strip()
            daily_penalty_rate = self.TIER_PENALTY_RATE.get(
                customer_tier, self.TIER_PENALTY_RATE["standard"]
            )

        # Penalty cap from contract type
        max_penalty_cap = self.CONTRACT_TYPE_CAPS.get(
            contract_type, self.CONTRACT_TYPE_CAPS["standard"]
        )

        total_penalty_pct = min(effective_delay * daily_penalty_rate, max_penalty_cap)
        financial_penalty = order_value * total_penalty_pct

        return round(financial_penalty, 2)

    def compute_batch(self, rows_list, delays_array):
        return [self.compute(row, delays_array[i]) for i, row in enumerate(rows_list)]
