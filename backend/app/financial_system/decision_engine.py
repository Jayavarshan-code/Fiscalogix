class DecisionEngine:
    def compute(self, row):
        """
        Translates REVM intelligence into deterministic Supply Chain actions utilizing absolute XAI (Explainable AI) 
        arrays to trace decisions back to their structural telemetry causes.
        """
        revm = row.get("revm", 0)
        risk_prob = row.get("risk_score", 0)
        confidence = row.get("risk_confidence", 0.5)
        
        # Explainability Data Extractors
        drivers = []
        action = "APPROVE EXECUTION"
        reason = "Structurally Positive REVM Yield"
        
        # Detect Dominant Causation
        time_cost = row.get("time_cost", 0)
        profit = row.get("contribution_profit", 1)  # Prevent div 0
        if time_cost > (profit * 0.35):
            drivers.append(f"time_cost_usd_burnden ({round(time_cost, 2)})")
            
        future_cost = row.get("future_cost", 0)
        if future_cost > (profit * 0.25):
            drivers.append(f"future_churn_expected ({round(future_cost, 2)})")
            
        delay = row.get("predicted_delay", 0)
        if delay > 4.0:
            drivers.append(f"predicted_delay_infraction ({round(delay, 1)} days)")
            
        # Core Decision Overrides
        if revm < 0:
            action = "CANCEL/DELAY SHIPMENT" if delay < 3.0 else "INTERVENE IMMEDIATELY"
            reason = "Terminal REVM is negative (Strict Capital Destruction)"
            drivers.append("Net-Negative System Yield")
            
        elif risk_prob > 0.7:
            action = "FLAG FOR C-SUITE REVIEW"
            reason = f"Catastrophic Contingency Risk Probability ({round(risk_prob*100, 1)}%)"
            drivers.append("Systemic Risk Matrix Threshold Breached")
            
        if not drivers:
            drivers.append("Standard Optimal Operational Matrices")

        return {
            "action": action,
            "reason": reason,
            "drivers": drivers,
            "confidence": round(confidence * (0.85 if revm < 0 else 0.98), 2)  # XAI Confidence decay
        }
