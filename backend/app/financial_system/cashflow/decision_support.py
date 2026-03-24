class CashflowDecisionSupport:
    def compute(self, shocks, root_causes):
        """
        Generates actionable supply chain decisions exactly when future shocks manifest.
        """
        recommendations = []
        
        for shock in shocks:
            if shock["type"] == "CASH_DEFICIT":
                recommendations.append({
                    "shock_date": shock["date"],
                    "action_type": "Financial",
                    "action": "EXPEDITE RECEIVABLES OR FACTOR INVOICES",
                    "reason": f"Critical cash deficit of ${shock['severity']} mathematically predicted."
                })
            elif shock["type"] == "LOW_LIQUIDITY":
                recommendations.append({
                    "shock_date": shock["date"],
                    "action_type": "Operational",
                    "action": "DELAY NON-CRITICAL PAYABLES",
                    "reason": f"Liquidity dips dangerously below safety threshold."
                })
            elif shock["type"] == "SUDDEN_DROP":
                recommendations.append({
                    "shock_date": shock["date"],
                    "action_type": "Strategic",
                    "action": "REDUCE INVENTORY EXPOSURE",
                    "reason": f"Sudden cash drain of ${shock['severity']} identified."
                })
                
        # Deduplicate recommendations based on date and action
        unique_recs = []
        seen = set()
        for r in recommendations:
            key = (r["shock_date"], r["action"])
            if key not in seen:
                seen.add(key)
                unique_recs.append(r)
                
        return unique_recs
