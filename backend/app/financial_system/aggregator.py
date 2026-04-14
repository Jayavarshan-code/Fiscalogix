class FinancialAggregator:

    def summarize(self, data):
        summary = {
            "total_revenue":   0,
            "total_cost":      0,
            "total_profit":    0,
            "total_revm":      0,
            "loss_shipments":  0,
            # Per-component cost breakdown — stamped onto each row by FinancialAgent
            "breakdown": {
                "delay_cost":        0,   # time_cost + fx_cost  (capital decay in transit)
                "penalty_cost":      0,   # sla_penalty + risk_penalty (contractual fines)
                "inventory_holding": 0,   # future_cost (holding burn / stockout risk)
                "opportunity_cost":  0,   # gst_cost + AR cost (working capital locked)
            },
        }

        for row in data:
            summary["total_revenue"]  += row.get("order_value", 0)
            summary["total_cost"]     += row.get("total_cost", 0)
            summary["total_profit"]   += row.get("contribution_profit", 0)
            summary["total_revm"]     += row.get("revm", 0)

            if row.get("revm", 0) < 0:
                summary["loss_shipments"] += 1

            # Aggregate cost components written by FinancialAgent.run_logic()
            summary["breakdown"]["delay_cost"]        += row.get("time_cost", 0) + row.get("fx_cost", 0)
            summary["breakdown"]["penalty_cost"]      += row.get("sla_penalty", 0) + row.get("risk_penalty", 0)
            summary["breakdown"]["inventory_holding"] += row.get("future_cost", 0)
            summary["breakdown"]["opportunity_cost"]  += row.get("gst_cost", 0)

        # Round all breakdown values for clean display
        bd = summary["breakdown"]
        for k in bd:
            bd[k] = round(bd[k], 2)

        return summary
