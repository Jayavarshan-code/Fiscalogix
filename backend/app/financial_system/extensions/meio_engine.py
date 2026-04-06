class MEIOEngine:
    """
    Multi-Echelon Inventory Optimization (MEIO). Simulated Q-learning heuristics calculating global warehouse load limits.
    """
    def compute(self, sku_data):
        """
        sku_data expects: {"sku": "A1", "global_inventory": 1000, "wacc": 0.08, "holding_cost_usd": 150.0, "stockout_penalty_usd": 500.0}
        """
        sku = sku_data.get("sku", "UNKNOWN")
        inv = sku_data.get("global_inventory", 1000)
        holding = sku_data.get("holding_cost_usd", 10.0)
        stockout = sku_data.get("stockout_penalty_usd", 100.0)

        # P3-7 FIX: Read wacc — it was accepted as input but never used.
        # WHAT WAS WRONG: projected_holding_wacc = inv × holding_cost, which is just
        # the raw physical storage cost. This ignores the opportunity cost of capital
        # tied up in inventory. The WACC-adjusted holding cost is:
        #   capital_carrying_cost = inventory_value × wacc
        # The true total holding cost = physical storage + capital carrying cost.
        # Without WACC, the engine always understated the cost of holding inventory,
        # biasing the alpha coefficient toward over-ordering and over-stocking.
        wacc = float(sku_data.get("wacc", 0.08))  # default 8% cost of capital

        # Mathematical approximation of Reinforcement Learning Policy Map
        # 3 Structural Hubs: NA (North America), EU (Europe), APAC (Asia)

        # Physical holding cost per unit × inventory units (annual storage spend)
        annual_storage_cost = inv * holding

        # Capital carrying cost: WACC applied to the inventory value (opportunity cost)
        # Uses holding_cost_usd as inventory unit value proxy when no separate value field
        inventory_value = inv * holding
        capital_carrying_cost = inventory_value * wacc

        # True economic holding cost = physical storage + cost of capital
        true_holding_cost = annual_storage_cost + capital_carrying_cost

        # RL coefficient comparing threat of stockouts vs TRUE total carrying costs
        # Previously used raw holding cost — now uses WACC-adjusted total
        alpha = stockout / max(1.0, (true_holding_cost / max(1, inv) + stockout))

        # Derived global safety stock allocations optimizing terminal loss
        alloc_na = int(inv * (0.45 * alpha))
        alloc_eu = int(inv * (0.35 * alpha))
        alloc_apac = inv - (alloc_na + alloc_eu)  # Sweep Remainder

        # Friction map
        projected_stockout_risk = (1.0 - alpha) * stockout * (inv * 0.1)

        return {
            "sku": sku,
            "optimal_allocation": {
                "NA_HUB": max(0, alloc_na),
                "EU_HUB": max(0, alloc_eu),
                "APAC_HUB": max(0, alloc_apac)
            },
            "financial_friction": {
                "projected_holding_wacc": round(true_holding_cost, 2),    # WACC-adjusted total
                "capital_carrying_cost":  round(capital_carrying_cost, 2), # WACC component surfaced
                "projected_stockout_risk": round(projected_stockout_risk, 2)
            }
        }
