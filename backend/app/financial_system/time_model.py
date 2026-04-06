class TimeValueModel:
    """
    Calculates two distinct time-based costs:
    1. Capital Opportunity Cost = OrderValue × WACC × (Δt / 365)
    2. Physical Pipeline Holding Cost = TotalCost × HoldingRate(cargo_type) × (Δt / 365)

    WHY THIS WAS FLAWED:
    Previously, holding_rate was a hardcoded 0.20 (20%) for ALL cargo types.
    20% is accurate for electronics but catastrophically wrong for:
      - Bulk grain / raw materials: ~5%
      - Automotive parts: ~18%
      - Pharmaceutical cold-chain: ~45%
      - Perishable food: ~60%
    Using 20% for pharmaceuticals would UNDERSTATE the cost by 55%.
    Using 20% for grain would OVERSTATE the cost by 300%.
    This inflated/deflated ReVM creates wrong APPROVE/CANCEL decisions.

    FIX: Cargo-type-aware lookup table with a safe general-cargo fallback.
    WACC is also now read from the per-row tenant config (defaults to 8% only
    when not explicitly supplied).
    """

    # Industry-standard annualized holding cost rates by cargo type
    # Sources: GS1, CSCMP Supply Chain Cost Benchmarks
    HOLDING_RATE_BY_CARGO = {
        "pharmaceutical":   0.45,   # Cold-chain, specialized storage
        "perishable":       0.60,   # Refrigerated, time-critical
        "electronics":      0.20,   # High-value, standard warehouse
        "automotive":       0.18,   # Bulky, moderate handling
        "textile":          0.12,   # Low-risk, standard bulk
        "chemical":         0.25,   # Hazmat storage premium
        "bulk_grain":       0.05,   # Commodity, low-cost silos
        "luxury":           0.30,   # High insurance, secure vaulting
        "general_cargo":    0.20,   # Industry average fallback
    }

    def compute(self, row, predicted_delay):
        if predicted_delay <= 0:
            return 0.0

        # 1. Capital Opportunity Cost
        # Read WACC from tenant row config; fall back to 8% industry average
        wacc = row.get("wacc", 0.08)
        if not wacc or wacc <= 0:
            wacc = 0.08
        order_value = row.get("order_value", 0.0)
        capital_cost = order_value * wacc * (predicted_delay / 365.0)

        # 2. Physical Holding / Pipeline Cost
        # Look up cargo-type-specific rate; default to general_cargo if unknown
        cargo_type = str(row.get("cargo_type", "general_cargo")).lower().strip()
        holding_rate = self.HOLDING_RATE_BY_CARGO.get(cargo_type, self.HOLDING_RATE_BY_CARGO["general_cargo"])
        total_cost = row.get("total_cost", 0.0)
        pipeline_cost = total_cost * holding_rate * (predicted_delay / 365.0)

        return round(capital_cost + pipeline_cost, 2)
