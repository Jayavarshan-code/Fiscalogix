class FinancialAggregator:

    def summarize(self, data):
        summary = {
            "total_revenue": 0,
            "total_cost": 0,
            "total_profit": 0,
            "total_revm": 0,
            "loss_shipments": 0
        }

        for row in data:
            summary["total_revenue"] += row["order_value"]
            summary["total_cost"] += row["total_cost"]
            summary["total_profit"] += row["contribution_profit"]
            summary["total_revm"] += row["revm"]

            if row["revm"] < 0:
                summary["loss_shipments"] += 1

        return summary
