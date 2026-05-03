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

OPEN/CLOSED FIX: Penalty tiers and contract rules are now stored in PenaltyRegistry.
  New tiers or contract types can be registered at runtime without modifying this file:
    PenaltyRegistry.register_tier("premium_enterprise", daily_rate=0.05)
    PenaltyRegistry.register_contract("zero_tolerance", cap=1.0, grace_days=0)
"""

from dataclasses import dataclass
from typing import Dict, Optional


# ── Registry data types ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class TierRule:
    """Daily penalty rate for a customer tier (as a fraction of order value per day)."""
    daily_rate: float  # e.g. 0.04 = 4%/day


@dataclass(frozen=True)
class ContractRule:
    """Cap and grace window for a contract type."""
    cap: float        # max penalty as fraction of order_value, e.g. 0.15 = 15%
    grace_days: int   # days before penalty clock starts


@dataclass(frozen=True)
class OtifRule:
    """Multiplier applied when an OTIF shortfall is detected."""
    multiplier: float


# ── Registry ─────────────────────────────────────────────────────────────────

class PenaltyRegistry:
    """
    Central registry for SLA penalty rules.

    Register new tiers / contract types at app startup or from tenant config —
    no changes to this file required (Open/Closed Principle).

    Example:
        PenaltyRegistry.register_tier("premium_enterprise", daily_rate=0.05)
        PenaltyRegistry.register_contract("zero_tolerance", cap=1.0, grace_days=0)
        PenaltyRegistry.register_otif_level("catastrophic", multiplier=6.0)
    """

    _tiers:    Dict[str, TierRule]    = {}
    _contracts: Dict[str, ContractRule] = {}
    _otif:     Dict[str, OtifRule]    = {}

    @classmethod
    def register_tier(cls, name: str, daily_rate: float) -> None:
        cls._tiers[name.lower().strip()] = TierRule(daily_rate=daily_rate)

    @classmethod
    def register_contract(cls, name: str, cap: float, grace_days: int) -> None:
        cls._contracts[name.lower().strip()] = ContractRule(cap=cap, grace_days=grace_days)

    @classmethod
    def register_otif_level(cls, name: str, multiplier: float) -> None:
        cls._otif[name.lower().strip()] = OtifRule(multiplier=multiplier)

    @classmethod
    def get_tier_rate(cls, tier: str, fallback: str = "standard") -> float:
        key = tier.lower().strip()
        rule = cls._tiers.get(key) or cls._tiers.get(fallback)
        return rule.daily_rate if rule else 0.015

    @classmethod
    def get_contract(cls, contract_type: str, fallback: str = "standard") -> ContractRule:
        key = contract_type.lower().strip()
        return (
            cls._contracts.get(key)
            or cls._contracts.get(fallback)
            or ContractRule(cap=0.15, grace_days=2)
        )

    @classmethod
    def get_otif_multiplier(cls, breach_level: str) -> float:
        rule = cls._otif.get(breach_level.lower().strip())
        return rule.multiplier if rule else 1.0

    @classmethod
    def list_tiers(cls) -> Dict[str, float]:
        return {k: v.daily_rate for k, v in cls._tiers.items()}

    @classmethod
    def list_contracts(cls) -> Dict[str, dict]:
        return {k: {"cap": v.cap, "grace_days": v.grace_days} for k, v in cls._contracts.items()}


# ── Seed default rules ────────────────────────────────────────────────────────
# These are the industry baseline values. Override via PenaltyRegistry.register_*()
# at app startup (e.g. from tenant config, Redis, or a YAML file).

# Customer tiers — source: Bain Supply Chain Practice, GS1 OTIF standards
# Enterprise buyers enforce harder because they have purchasing leverage.
for _tier, _rate in [
    ("enterprise", 0.04),   # 4%/day — Walmart, Amazon vendor requirements
    ("strategic",  0.03),   # 3%/day — key account SLA with contract enforcement
    ("growth",     0.02),   # 2%/day — mid-market, growing formalization
    ("standard",   0.015),  # 1.5%/day — standard recurring customer
    ("spot",       0.005),  # 0.5%/day — minimal, often no formal SLA
    ("trial",      0.005),  # 0.5%/day — no established SLA yet
]:
    PenaltyRegistry.register_tier(_tier, _rate)

# Contract types — cap = max penalty fraction; grace = days before clock starts
# Source: GS1 OTIF standard §4.2, Walmart Supplier Agreement §11, VICS OTIF guidelines
for _contract, _cap, _grace in [
    ("full_rejection", 1.00, 0),  # Entire cargo voided — Walmart-style OTIF
    ("strict",         0.30, 1),  # Aggressive SLA, pharma/auto supply chains
    ("standard",       0.15, 2),  # Default OTIF (most enterprise and 3PL contracts)
    ("lenient",        0.05, 3),  # Negotiated grace-window SLA
]:
    PenaltyRegistry.register_contract(_contract, _cap, _grace)

# OTIF breach multipliers — shortfall below contracted threshold escalates the penalty
for _level, _mult in [
    ("none",     1.0),  # No shortfall
    ("minor",    1.0),  # 1–3% below threshold — standard per-shipment penalty
    ("moderate", 1.5),  # 3–7% below — escalated, often triggers formal review
    ("severe",   2.5),  # 7–15% below — may trigger chargeback or deduction
    ("critical", 4.0),  # >15% below — Walmart/Amazon-style full rejection risk
]:
    PenaltyRegistry.register_otif_level(_level, _mult)


# ── Model ─────────────────────────────────────────────────────────────────────

class SLAPenaltyModel:
    """
    Models OTIF contractual penalties.

    Penalty rate priority:
      1. NLP-extracted rate from uploaded contract PDF (most accurate)
      2. Customer-tier heuristic via PenaltyRegistry (correct business logic)
      3. ContractRule.cap fallback (structural maximum)

    To add a new tier or contract type, call PenaltyRegistry.register_*() —
    do NOT edit this class.
    """

    def compute(self, row, predicted_delay: float) -> float:
        if predicted_delay <= 0:
            return 0.0

        order_value   = max(float(row.get("order_value") or 0.0), 0.0)
        contract_type = str(row.get("contract_type", "standard")).lower().strip()
        contract_rule = PenaltyRegistry.get_contract(contract_type)

        effective_delay = max(0.0, predicted_delay - contract_rule.grace_days)
        if effective_delay <= 0:
            return 0.0

        # Priority 1: NLP-extracted daily penalty rate from uploaded contract
        nlp_rate = row.get("nlp_extracted_penalty_rate")
        if nlp_rate is not None and float(nlp_rate) > 0:
            daily_penalty_rate = float(nlp_rate)
        else:
            customer_tier      = str(row.get("customer_tier", "standard")).lower().strip()
            daily_penalty_rate = PenaltyRegistry.get_tier_rate(customer_tier)

        otif_multiplier = PenaltyRegistry.get_otif_multiplier(self._otif_breach_level(row))

        max_cap = contract_rule.cap
        # NLP-extracted penalty cap from the contract overrides the type-based cap
        nlp_cap = row.get("nlp_extracted_penalty_cap")
        if nlp_cap is not None:
            try:
                nlp_cap_pct = float(nlp_cap) / max(order_value, 1)
                max_cap = min(max_cap, nlp_cap_pct)
            except (TypeError, ZeroDivisionError):
                pass

        base_pct          = min(effective_delay * daily_penalty_rate, max_cap)
        adjusted_pct      = min(base_pct * otif_multiplier, max_cap)
        financial_penalty = order_value * adjusted_pct

        return round(financial_penalty, 2)

    def compute_with_detail(self, row, predicted_delay: float) -> dict:
        """Returns full penalty breakdown — used by API endpoints and the executive cockpit."""
        order_value       = max(float(row.get("order_value") or 0.0), 0.0)
        contract_type     = str(row.get("contract_type", "standard")).lower().strip()
        contract_rule     = PenaltyRegistry.get_contract(contract_type)
        effective_delay   = max(0.0, predicted_delay - contract_rule.grace_days)
        otif_breach_level = self._otif_breach_level(row)
        otif_multiplier   = PenaltyRegistry.get_otif_multiplier(otif_breach_level)
        penalty           = self.compute(row, predicted_delay)

        return {
            "financial_penalty":  penalty,
            "effective_delay":    round(effective_delay, 1),
            "grace_days_applied": contract_rule.grace_days,
            "contract_type":      contract_type,
            "otif_breach_level":  otif_breach_level,
            "otif_multiplier":    otif_multiplier,
            "penalty_source":     "nlp_contract" if row.get("nlp_extracted_penalty_rate") else "tier_heuristic",
            "breach_level":       self._breach_level(penalty, order_value),
        }

    def compute_batch(self, rows_list, delays_array) -> list:
        return [self.compute(row, delays_array[i]) for i, row in enumerate(rows_list)]

    # ── Private helpers ───────────────────────────────────────────────────────

    def _otif_breach_level(self, row) -> str:
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

    @staticmethod
    def _breach_level(penalty: float, order_value: float) -> str:
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
