class FinancialAggregator:

    def summarize_shipments(self, data):
        summary = {
            "total_profit": 0,
            "total_revenue": 0,
            "total_cost": 0,
            "loss_shipments": 0,
            "high_margin_shipments": 0,
            "total_ar_cost": 0
        }

        for row in data:
            summary["total_profit"] += row["profit"]
            summary["total_revenue"] += row["order_value"]
            summary["total_cost"] += row["total_cost"]
            if "ar_cost" in row:
                summary["total_ar_cost"] += row["ar_cost"]

            if row["profit"] < 0:
                summary["loss_shipments"] += 1

            if row["profit"] > row["order_value"] * 0.3:
                summary["high_margin_shipments"] += 1

        return summary
        
    def summarize_inventory(self, data):
        summary = {
            "total_capital_locked": 0,
            "total_inventory_opportunity_cost": 0
        }
        
        for row in data:
            summary["total_capital_locked"] += row["capital_locked"]
            summary["total_inventory_opportunity_cost"] += row["inventory_opportunity_cost"]
            
        return summary