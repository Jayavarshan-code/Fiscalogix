import numpy as np

class MonteCarloEngine:
    """
    Pillar 18: Stochastic Value-at-Risk (VaR) mapping.
    Executes an N-cycle random walk probabilistically simulating absolute Supply Chain collapse
    possibilities to extract the rigid 95% Confidence Floor.
    """
    def simulate_var(self, enriched_records, iterations=1000):
        if not enriched_records:
            return {}

        baseline_total_revm = sum(r.get("revm", 0.0) for r in enriched_records)
        np.random.seed(42) # Explicit seeding for deterministic audits
        
        simulated_outcomes = []
        for _ in range(iterations):
            sim_revm = 0
            for r in enriched_records:
                 base_profit = float(r.get("contribution_profit", 0.0))
                 
                 # Random walk Delay against a Poisson distribution (captures discrete event shocks)
                 base_delay = r.get("predicted_delay", 2)
                 sim_delay = np.random.poisson(base_delay if base_delay >= 0 else 0)
                 
                 # Random walk Cost based on Normal algorithmic variance (10% standard deviation)
                 base_cost = float(r.get("total_cost", 5000))
                 sim_cost = np.random.normal(base_cost, base_cost * 0.1)
                 
                 # Reconstruct core REVM dependencies via shifted inputs
                 risk_penalty = float(r.get("risk_score", 0.05)) * float(r.get("order_value", 0))
                 time_cost = sim_cost * (float(r.get("wacc", 0.08)) / 365.0) * sim_delay
                 fx_cost = float(r.get("fx_cost", 0.0)) # Static holding penalty
                 
                 sim_revm += (base_profit - risk_penalty - time_cost - fx_cost)
                 
            simulated_outcomes.append(sim_revm)
             
        # Extract the Gaussian 95% Confidence Value at Risk boundary
        var_95 = np.percentile(simulated_outcomes, 5)
        worst_case = np.min(simulated_outcomes)
        
        return {
            "baseline_revm": round(baseline_total_revm, 2),
            "stochastic_var_95_revm": round(var_95, 2),
            "absolute_maximum_loss_floor": round(worst_case, 2),
            "simulations_executed_cycles": iterations
        }
