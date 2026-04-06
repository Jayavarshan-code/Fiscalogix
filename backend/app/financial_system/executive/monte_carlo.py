import numpy as np

# ---------------------------------------------------------------------------
# FIX APPLIED — Vulnerability: Unbounded Pareto Explosion
#
# WHAT WAS WRONG:
# np.random.pareto(alpha=1.5) has a defined mean but INFINITE variance.
# In a 1,000-cycle simulation, the pareto_shock array will occasionally
# sample astronomically large values (e.g., a simulated delay of 3,500+ days).
# These extreme outliers then propagate through the SLA and TimeValue models,
# producing absurdities like "$500M loss on a $10K shipment" — destroying
# the statistical integrity of the entire VaR floor calculation.
#
# WHY IT'S DANGEROUS:
# A CFO seeing a VaR floor of -$750 Million on a $200K shipment portfolio
# will immediately dismiss the entire system as broken. Worse, if the garbage
# outlier doesn't happen to appear in the top-20 scenario samples surfaced on
# the dashboard, it silently corrupts the `absolute_maximum_loss_floor` figure
# that risk officers use for capital reserve planning.
#
# HOW IT WAS FIXED:
# np.clip() caps the pareto_shock to a physically meaningful maximum.
# 180 days is used as the hard ceiling — the longest real-world disruption
# on record (COVID-19 port congestion, Suez Canal blockage) was ~90-120 days.
# 180 days is a conservative upper bound that keeps the simulation grounded.
# The cap is a named constant (MAX_BLACK_SWAN_DELAY_DAYS) for auditability.
# ---------------------------------------------------------------------------

# Maximum plausible delay in a catastrophic geopolitical / logistics event.
# Based on: Suez Canal blockage (6 days), COVID port congestion (~90 days),
# Russia-Ukraine Black Sea closure (~120 days). 180-day cap = extreme upper bound.
MAX_BLACK_SWAN_DELAY_DAYS = 180


class MonteCarloEngine:
    """
    Pillar 18: Stochastic Value-at-Risk (VaR) mapping.
    Executes N-cycle random walk probabilistically simulating Supply Chain
    collapse scenarios to extract the 95% Confidence REVM Floor.

    Distribution model:
    - Costs:  Log-Normal (fat-tailed, always positive, right-skewed)
    - Delays: Poisson base + Pareto Black Swan (CAPPED at 180 days)
    """

    def simulate_var(self, enriched_records, iterations=1000):
        if not enriched_records:
            return {}

        baseline_total_revm = sum(r.get("revm", 0.0) for r in enriched_records)
        np.random.seed(42)  # Deterministic seed for auditable results

        # --- Build dense NumPy arrays ---
        base_profits   = np.array([float(r.get("contribution_profit", 0.0)) for r in enriched_records])
        base_delays    = np.array([max(0, r.get("predicted_delay", 2))       for r in enriched_records])
        base_costs     = np.array([float(r.get("total_cost", 5000.0))         for r in enriched_records])
        risk_penalties = np.array([float(r.get("risk_score", 0.05)) * float(r.get("order_value", 0)) for r in enriched_records])
        waccs          = np.array([float(r.get("wacc", 0.08))                for r in enriched_records])
        fx_costs       = np.array([float(r.get("fx_cost", 0.0))              for r in enriched_records])
        sla_penalties  = np.array([float(r.get("sla_penalty", 0.0))          for r in enriched_records])

        n = len(enriched_records)

        # --- Delay Simulation: Poisson base + Pareto Black Swan overlay (CAPPED) ---
        sim_delays = np.random.poisson(base_delays, size=(iterations, n)).astype(float)

        # Black Swan: 5% of iterations experience a catastrophic delay
        black_swan_mask = np.random.random(size=(iterations, n)) < 0.05
        pareto_raw      = np.random.pareto(1.5, size=(iterations, n)) * base_delays

        # ✅ CRITICAL FIX: Clip Pareto output to physically meaningful maximum.
        # Without this, pareto_raw occasionally produces values like 3,500+ days,
        # which propagate as garbage into time/SLA models and destroy VaR integrity.
        pareto_shock = np.clip(pareto_raw, 0, MAX_BLACK_SWAN_DELAY_DAYS)

        sim_delays = np.where(black_swan_mask, sim_delays + pareto_shock, sim_delays)

        # --- Cost Simulation: Log-Normal (fat-tailed, always positive) ---
        cv       = 0.30  # 30% coefficient of variation — logistics industry standard
        sigma_ln = np.sqrt(np.log(1 + cv**2))
        mu_ln    = np.log(np.maximum(base_costs, 1.0)) - (sigma_ln**2 / 2)
        sim_costs = np.random.lognormal(mu_ln, sigma_ln, size=(iterations, n))

        # --- Time-Value of Money ---
        time_costs = sim_costs * (waccs / 365.0) * sim_delays

        # --- Full ReVM simulation: all 5 cost components ---
        sim_revm_matrix  = base_profits - risk_penalties - time_costs - fx_costs - sla_penalties
        simulated_outcomes = np.sum(sim_revm_matrix, axis=1)

        var_95     = np.percentile(simulated_outcomes, 5)
        worst_case = np.min(simulated_outcomes)

        return {
            "baseline_revm":               round(baseline_total_revm, 2),
            "stochastic_var_floor_95pct":  round(var_95, 2),
            "absolute_maximum_loss_floor": round(worst_case, 2),
            "simulations_executed_cycles": iterations,
            "distribution_model":          f"Log-Normal costs + Poisson delays + Pareto Black Swan (5%, capped {MAX_BLACK_SWAN_DELAY_DAYS}d)",
            "scenarios": [round(float(x), 2) for x in simulated_outcomes[:20]]
        }
