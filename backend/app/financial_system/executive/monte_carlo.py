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

# Default daily SLA penalty rate used when no contract data is available.
# Industry standard OTIF: 1.5% per day for standard contracts.
_DEFAULT_DAILY_PENALTY_RATE = 0.015

# SLA contract-type caps — mirrors SLAPenaltyModel.CONTRACT_TYPE_CAPS exactly.
# Kept here so the Monte Carlo can apply the same caps under stressed delays
# without importing the SLA model (avoids circular dependency).
_SLA_CONTRACT_CAPS = {
    "full_rejection": 1.00,
    "strict":         0.30,
    "standard":       0.15,
    "lenient":        0.05,
}


class MonteCarloEngine:
    """
    Pillar 18: Stochastic Value-at-Risk (VaR) mapping.
    Executes N-cycle random walk probabilistically simulating Supply Chain
    collapse scenarios to extract the 95% Confidence REVM Floor.

    Distribution model:
    - Costs:  Log-Normal (fat-tailed, always positive, right-skewed)
    - Delays: Poisson base + Pareto Black Swan (CAPPED at 180 days)

    GAP 12 FIX:
    SLA penalties are now re-computed per simulation cycle using the
    stressed sim_delays, not the baseline predicted_delay values.
    Before this fix, a 45-day black-swan draw still used the 2-day
    baseline SLA penalty — understating downside risk by up to 15x
    on strict/full-rejection contracts.
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

        # ── GAP 12 FIX: SLA inputs for re-computation under stressed delays ────
        # Extract per-row inputs from enriched records so the simulation can
        # recompute sla_penalty = min(sim_delay × daily_rate × order_value, cap)
        # for every iteration, just as SLAPenaltyModel.compute() would.
        order_values  = np.array([float(r.get("order_value", 0.0))  for r in enriched_records])
        daily_rates   = np.array([
            float(r.get("nlp_extracted_penalty_rate", None) or
                  (0.03 if r.get("credit_days", 30) <= 30 else _DEFAULT_DAILY_PENALTY_RATE))
            for r in enriched_records
        ])
        sla_caps = np.array([
            _SLA_CONTRACT_CAPS.get(
                str(r.get("contract_type", "standard")).lower().strip(),
                _SLA_CONTRACT_CAPS["standard"]
            ) * float(r.get("order_value", 0.0))   # cap in absolute $ terms
            for r in enriched_records
        ])

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

        # --- GAP 12 FIX: SLA penalties re-computed under stressed sim_delays ──
        #
        # OLD (broken):
        #   sim_revm_matrix = ... - sla_penalties   ← static 2-day baseline value
        #   If sim_delays draws 45 days, SLA stays at the 2-day amount.
        #   A strict contract's 30% cap was never tested under black-swan stress.
        #
        # NEW (correct):
        #   sim_sla_raw[i, j] = sim_delays[i, j] × daily_rate[j] × order_value[j]
        #   sim_sla[i, j]     = min(sim_sla_raw[i, j], sla_cap[j])   ← cap in $
        #   This mirrors exactly what SLAPenaltyModel.compute() does, but
        #   vectorised across all iterations × shipments in one NumPy op.
        #
        # Shape broadcast: sim_delays (I×N) × daily_rates (N,) × order_values (N,)
        sim_sla_raw = sim_delays * daily_rates[np.newaxis, :] * order_values[np.newaxis, :]
        sim_sla     = np.minimum(sim_sla_raw, sla_caps[np.newaxis, :])

        # --- Full ReVM simulation: all 5 cost components ---
        sim_revm_matrix    = base_profits - risk_penalties - time_costs - fx_costs - sim_sla
        simulated_outcomes = np.sum(sim_revm_matrix, axis=1)

        var_95     = np.percentile(simulated_outcomes, 5)
        worst_case = np.min(simulated_outcomes)

        # Compute baseline SLA total for transparency (what the static model showed)
        baseline_sla_total = float(np.sum(
            np.minimum(base_delays * daily_rates * order_values, sla_caps)
        ))

        return {
            "baseline_revm":               round(baseline_total_revm, 2),
            "var_95":                      round(var_95, 2),           # shorthand alias
            "stochastic_var_floor_95pct":  round(var_95, 2),           # backward compat
            "absolute_maximum_loss_floor": round(worst_case, 2),
            "simulations_executed_cycles": iterations,
            "distribution_model":          (
                f"Log-Normal costs + Poisson delays + Pareto Black Swan "
                f"(5%, capped {MAX_BLACK_SWAN_DELAY_DAYS}d) | "
                f"SLA re-computed under stress (Gap-12 fix)"
            ),
            "baseline_sla_total":          round(baseline_sla_total, 2),
            "scenarios": [round(float(x), 2) for x in simulated_outcomes[:20]],
        }
