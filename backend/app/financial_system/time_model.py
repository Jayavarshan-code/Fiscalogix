"""
TimeValueModel — capital opportunity cost + physical pipeline holding cost.

P1-C FIX: total_cost used as the pipeline holding cost base.
WHAT WAS WRONG:
  `pipeline_cost = total_cost * holding_rate * (delay / 365.0)`
  `total_cost` in the data row is the FULL computed logistics cost (shipment_cost +
  delay_cost + penalties + opportunity_cost). Using it as the holding cost base
  creates two problems:
    1. Circular dependency: total_cost includes time_cost which we're computing now.
       On the first run, total_cost is the SQL-computed value from the financial
       query — which is correct. But on subsequent in-memory enrichment passes,
       total_cost may already include prior time_model outputs.
    2. Silent zero: If total_cost is missing or zero (new shipment, no prior run),
       pipeline_cost silently returns 0 — understating holding cost entirely.

FIX: Use shipment_cost as the pipeline holding base (the physical cost of moving
  the goods, not the total computed financial impact). Fall back to
  order_value × cargo_value_ratio when shipment_cost is also missing.

Gap-6 FIX (Dynamic WACC Engine):
  WACC no longer comes from a hardcoded fallback or per-row ERP export alone.
  WACCEngine.resolve() applies a 3-tier hierarchy:
    Tier 1 — per-tenant Redis override (set by admin API)
    Tier 2 — industry-vertical Damodaran benchmark, adjusted for current 10yr UST
    Tier 3 — 8.5% hardcoded fallback
  This means time_cost now tracks the real cost of capital rather than freezing
  the 2019 near-zero-rate environment.
"""

import logging
from app.financial_system.wacc_engine import WACCEngine

logger = logging.getLogger(__name__)

# Module-level singleton — constructed once, Redis connection reused per request.
_wacc_engine = WACCEngine()


class TimeValueModel:
    """
    Two cost components:
      1. Capital Opportunity Cost = order_value × WACC × (delay_days / 365)
      2. Physical Pipeline Holding = shipment_cost × holding_rate(cargo_type) × (delay_days / 365)

    WACC is now resolved dynamically per row via WACCEngine (Gap-6 fix).
    """

    # Annualized holding cost rates by cargo type (unchanged — already correct)
    # Source: GS1, CSCMP Supply Chain Cost Benchmarks
    HOLDING_RATE_BY_CARGO = {
        "pharmaceutical":  0.45,
        "perishable":      0.60,
        "electronics":     0.20,
        "automotive":      0.18,
        "textile":         0.12,
        "chemical":        0.25,
        "bulk_grain":      0.05,
        "luxury":          0.30,
        "general_cargo":   0.20,
    }

    # P1-C FIX: Cargo value ratio fallback when both shipment_cost and total_cost are 0.
    # Represents typical logistics cost as % of order value by cargo type.
    # Used ONLY when no cost data is available — prevents silent zero.
    LOGISTICS_COST_RATIO = {
        "pharmaceutical":  0.12,
        "perishable":      0.18,
        "electronics":     0.08,
        "automotive":      0.10,
        "textile":         0.15,
        "chemical":        0.14,
        "bulk_grain":      0.20,
        "luxury":          0.06,
        "general_cargo":   0.12,
    }

    def compute(self, row, predicted_delay, tenant_id: str = "default_tenant"):
        if predicted_delay <= 0:
            return 0.0

        # 1. Capital Opportunity Cost — Gap-6 fix: dynamic WACC via WACCEngine
        try:
            wacc = _wacc_engine.resolve(row, tenant_id=tenant_id)
        except Exception as e:
            # Defensive: engine should never throw, but if Redis explodes, fall back.
            logger.debug(f"TimeValueModel: WACCEngine.resolve() failed ({e}), using 0.085.")
            wacc = row.get("wacc", 0.085)
            if not wacc or wacc <= 0:
                wacc = 0.085
            if wacc > 1.0:
                wacc /= 100.0

        order_value  = row.get("order_value", 0.0)
        capital_cost = order_value * wacc * (predicted_delay / 365.0)

        # 2. Physical Pipeline Holding Cost
        cargo_type = str(row.get("cargo_type", "general_cargo")).lower().strip()
        holding_rate = self.HOLDING_RATE_BY_CARGO.get(
            cargo_type, self.HOLDING_RATE_BY_CARGO["general_cargo"]
        )

        # P1-C FIX: Use shipment_cost as the base, not total_cost
        shipment_cost = row.get("shipment_cost", None)
        if shipment_cost and shipment_cost > 0:
            holding_base = shipment_cost
        else:
            # Fallback: estimate shipment cost from order_value × logistics cost ratio
            # Prevents silent zero when shipment has no cost data yet
            ratio = self.LOGISTICS_COST_RATIO.get(
                cargo_type, self.LOGISTICS_COST_RATIO["general_cargo"]
            )
            holding_base = order_value * ratio

        pipeline_cost = holding_base * holding_rate * (predicted_delay / 365.0)

        return round(capital_cost + pipeline_cost, 2)
