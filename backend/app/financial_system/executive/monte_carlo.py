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
        np.random.seed(42)  # Explicit seeding for deterministic audits
        
        # --- Vectorized Matrix Initialization ---
        base_profits = np.array([float(r.get("contribution_profit", 0.0)) for r in enriched_records])
        base_delays = np.array([max(0, r.get("predicted_delay", 2)) for r in enriched_records])
        base_costs = np.array([float(r.get("total_cost", 5000)) for r in enriched_records])
        risk_penalties = np.array([float(r.get("risk_score", 0.05)) * float(r.get("order_value", 0)) for r in enriched_records])
        waccs = np.array([float(r.get("wacc", 0.08)) for r in enriched_records])
        fx_costs = np.array([float(r.get("fx_cost", 0.0)) for r in enriched_records])
        # Fix: SLA penalties were absent from the simulation — now correctly included
        sla_penalties = np.array([float(r.get("sla_penalty", 0.0)) for r in enriched_records])

        num_records = len(enriched_records)

        # --- Massive Matrix Simulation  ---
        sim_delays = np.random.poisson(base_delays, size=(iterations, num_records))
        sim_costs = np.random.normal(base_costs, base_costs * 0.1, size=(iterations, num_records))
        
        # Time-value of money cost per scenario
        time_costs = sim_costs * (waccs / 365.0) * sim_delays
        
        # Full ReVM simulation — all 5 cost components included
        # Shape: (iterations, num_records)
        sim_revm_matrix = base_profits - risk_penalties - time_costs - fx_costs - sla_penalties
        
        # Sum across shipments for each iteration → total portfolio outcome
        simulated_outcomes = np.sum(sim_revm_matrix, axis=1)
             
        # 95% VaR: In 95% of scenarios, portfolio REVM exceeds this floor
        var_95 = np.percentile(simulated_outcomes, 5)
        worst_case = np.min(simulated_outcomes)
        
        return {
            "baseline_revm": round(baseline_total_revm, 2),
            "stochastic_var_floor_95pct": round(var_95, 2),  # Renamed for clarity
            "absolute_maximum_loss_floor": round(worst_case, 2),
            "simulations_executed_cycles": iterations,
            "performance_mode": "Vectorized (Sub-Second)",
            "scenarios": [round(float(x), 2) for x in simulated_outcomes[:20]]
        }
