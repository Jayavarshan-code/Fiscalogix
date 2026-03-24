class ActionSimulator:
    def __init__(self, risk, time, future):
        """
        Imports active predictive ML models to exactly recompute systemic mathematical risk and value.
        """
        self.risk = risk
        self.time = time
        self.future = future
        
    def simulate_scenarios(self, action_row, num_scenarios=200):
        """
        Tech Giant Upgrade: Stochastic Scenario Generation.
        Generates N parallel futures for a single action branch to identify its 'Regret' profile.
        """
        if action_row["action_name"] == "CANCEL":
            return [0.0] * num_scenarios
            
        import numpy as np
        
        # 1. Base Variables
        base_demand = action_row.get("predicted_demand", 100)
        base_risk = self.risk.compute(action_row, action_row.get("delay_days", 0))["score"]
        
        # 2. Perturb Reality (Stochastic Shocks)
        # We model Demand as a Normal Distribution and Risk as a Beta Distribution
        demand_scenarios = np.random.normal(base_demand, base_demand * 0.3, num_scenarios)
        risk_scenarios = np.random.beta(2, 5, num_scenarios) * (1.5 if base_risk > 0.5 else 1.0)
        
        results = []
        for d, r in zip(demand_scenarios, risk_scenarios):
            # Re-compute ReVM for this specific 'Future World'
            profit = action_row.get("order_value", 0) - action_row.get("total_cost", 0)
            
            # Temporal Risk VaR
            is_critical = action_row.get("is_critical", False)
            risk_mult = 3.0 if is_critical else 1.0
            risk_pen = r * action_row.get("order_value", 0) * risk_mult
            
            # Customer Behavioural Destruction
            future_cost = self.future.compute(action_row, action_row.get("delay_days", 0), d)
            if is_critical and action_row.get("delay_days", 0) > 0:
                future_cost *= 2.0
                
            sim_revm = profit - risk_pen - future_cost
            results.append(round(float(sim_revm), 2))
            
        return results
