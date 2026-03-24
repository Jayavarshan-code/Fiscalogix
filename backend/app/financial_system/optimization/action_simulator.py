class ActionSimulator:
    def __init__(self, risk, time, future):
        """
        Imports active predictive ML models to exactly recompute systemic mathematical risk and value.
        """
        self.risk = risk
        self.time = time
        self.future = future
        
    def simulate(self, action_row, predicted_demand=None):
        """
        Re-executes the global REVM equations natively across the synthesized Candidate Action.
        """
        if action_row["action_name"] == "CANCEL":
            return 0.0 # Absolute zero reality
            
        # 1. Update gross foundation
        action_row["contribution_profit"] = action_row.get("order_value", 0) - action_row.get("total_cost", 0)
        
        # 2. Risk Re-Execution (Now utilizing optimized delays/costs)
        risk_out = self.risk.compute(action_row, action_row.get("delay_days", 0))
        risk_pen = risk_out["score"] * action_row.get("order_value", 0)
        
        # 3. Time Value
        time_cost = self.time.compute(action_row)
        
        # 4. Behavioral Destruction
        demand = predicted_demand if predicted_demand else action_row.get("predicted_demand", 0)
        future_cost = self.future.compute(action_row, action_row.get("delay_days", 0), demand)
        
        # 💥 Recompute Unified Value
        simulated_revm = action_row["contribution_profit"] - risk_pen - time_cost - future_cost
        
        return round(simulated_revm, 2)
