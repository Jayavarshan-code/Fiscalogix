import numpy as np
from scipy.stats import norm as _norm

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

# Tier-based daily penalty rates — mirrors SLAPenaltyModel.TIER_PENALTY_RATE.
# Used in Monte Carlo to replace the old stale credit_days heuristic.
_TIER_PENALTY_RATES = {
    "enterprise": 0.04,
    "strategic":  0.03,
    "growth":     0.02,
    "standard":   0.015,
    "spot":       0.005,
    "trial":      0.005,
}

# SLA contract-type caps — mirrors SLAPenaltyModel.CONTRACT_TYPE_CAPS exactly.
_SLA_CONTRACT_CAPS = {
    "full_rejection": 1.00,
    "strict":         0.30,
    "standard":       0.15,
    "lenient":        0.05,
}

# Grace periods — mirrors SLAPenaltyModel.GRACE_PERIOD_BY_CONTRACT.
# Applied per-cycle so stressed delays are also grace-adjusted before penalty math.
_SLA_GRACE_DAYS = {
    "full_rejection": 0,
    "strict":         1,
    "standard":       2,
    "lenient":        3,
}


class MonteCarloEngine:
    """
    Pillar 18: Stochastic Value-at-Risk (VaR) mapping.
    Executes N-cycle random walk probabilistically simulating Supply Chain
    collapse scenarios to extract the 95% Confidence REVM Floor.

    Distribution model:
    - Costs:  Log-Normal (fat-tailed, always positive, right-skewed)
    - Delays: Poisson base (independent) + Correlated Pareto Black Swan
              (Gaussian copula via Cholesky, capped at 180 days)

    Gap fixes applied:
    - Gap-12:  SLA penalties re-computed per cycle under stressed delays
    - Gap-P3:  Grace period applied before SLA clock starts
    - Gap-VaR-1: Default raised to 10,000 cycles (Basel III minimum)
    - Gap-VaR-2: Cholesky correlation matrix — same-route black-swan events
                 are now correlated (port strike hits ALL CN→EU shipments,
                 not just 5% drawn independently). Without this, the Law of
                 Large Numbers suppresses tail risk for correlated portfolios.
    """

    @staticmethod
    def _build_correlation_matrix(enriched_records):
        """
        Builds an N×N route-similarity correlation matrix.

        Correlation logic (Gaussian copula, industry-calibrated):
          same full route  → 0.75  (e.g. both CN-EU: same port, same congestion)
          same origin      → 0.35  (e.g. CN-EU and CN-US: same origin port risk)
          same destination → 0.20  (e.g. CN-EU and US-EU: same arrival port)
          otherwise        → 0.05  (low background correlation)

        The matrix is guaranteed positive-definite via eigenvalue floor clipping,
        which is required for Cholesky decomposition to succeed numerically.
        """
        n = len(enriched_records)
        routes = [str(r.get("route", "LOCAL")).upper().strip() for r in enriched_records]

        # Parse origin and destination from "ORIGIN-DEST" format
        origins = [rt.split("-")[0] if "-" in rt else rt for rt in routes]
        dests   = [rt.split("-")[1] if "-" in rt else ""  for rt in routes]

        C = np.eye(n, dtype=float)
        for i in range(n):
            for j in range(i + 1, n):
                if routes[i] == routes[j]:
                    rho = 0.75   # identical route — same port congestion / strike exposure
                elif origins[i] == origins[j] and origins[i] != "LOCAL":
                    rho = 0.35   # same origin hub
                elif dests[i] == dests[j] and dests[i] != "":
                    rho = 0.20   # same destination port
                else:
                    rho = 0.05   # cross-region background correlation
                C[i, j] = C[j, i] = rho

        # Nearest positive-definite projection via eigenvalue floor.
        # Required when a single-route portfolio produces a rank-deficient C.
        eigvals, eigvecs = np.linalg.eigh(C)
        eigvals = np.maximum(eigvals, 1e-8)
        C_pd = eigvecs @ np.diag(eigvals) @ eigvecs.T
        # Re-normalise diagonal to exactly 1.0 (eigh may introduce tiny float drift)
        d = np.sqrt(np.diag(C_pd))
        C_pd = C_pd / np.outer(d, d)
        return C_pd

    def simulate_var(self, enriched_records, iterations=10000):
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

        # Use tier-based rate (consistent with SLAPenaltyModel.TIER_PENALTY_RATE after P1-B fix).
        # The old credit_days heuristic (0.03 if ≤30 else 0.015) was semantically inverted
        # and has been replaced everywhere. NLP-extracted rate still takes priority.
        daily_rates   = np.array([
            float(r.get("nlp_extracted_penalty_rate", None) or
                  _TIER_PENALTY_RATES.get(
                      str(r.get("customer_tier", "standard")).lower().strip(),
                      _DEFAULT_DAILY_PENALTY_RATE
                  ))
            for r in enriched_records
        ])
        sla_caps = np.array([
            _SLA_CONTRACT_CAPS.get(
                str(r.get("contract_type", "standard")).lower().strip(),
                _SLA_CONTRACT_CAPS["standard"]
            ) * float(r.get("order_value", 0.0))   # cap in absolute $ terms
            for r in enriched_records
        ])

        # Grace period per shipment — subtracted from sim_delays before penalty math.
        # Mirrors SLAPenaltyModel.GRACE_PERIOD_BY_CONTRACT so stressed scenarios
        # apply the same contractual grace as the deterministic model.
        grace_days = np.array([
            float(_SLA_GRACE_DAYS.get(
                str(r.get("contract_type", "standard")).lower().strip(),
                _SLA_GRACE_DAYS["standard"]
            ))
            for r in enriched_records
        ])

        n = len(enriched_records)

        # --- Delay Simulation: Poisson base (independent) ---
        # Individual carrier/lane variance is genuinely uncorrelated — each shipment
        # has its own operational jitter independent of others on the same route.
        sim_delays = np.random.poisson(base_delays, size=(iterations, n)).astype(float)

        # --- Correlated Black Swan via Gaussian Copula (Cholesky) ---
        #
        # WHY CORRELATION MATTERS:
        # Without this, black-swan events are drawn independently for each shipment.
        # A 5% chance on 100 CN→EU shipments means ~5 are hit per iteration.
        # In reality, a Red Sea port strike hits ALL 100 simultaneously.
        # Independent simulation lets the Law of Large Numbers suppress this
        # portfolio-level tail risk — VaR is understated by 30–50% for
        # concentrated-route portfolios.
        #
        # HOW IT WORKS (Gaussian copula):
        # 1. Build route-similarity correlation matrix C (N×N)
        # 2. Cholesky factor: L = chol(C), where C = L @ L.T
        # 3. Draw iid standard normals Z ~ N(0, I), shape (iterations, N)
        # 4. Correlate: corr_Z = (L @ Z.T).T — now correlated standard normals
        # 5. Map to uniform: U = Φ(corr_Z) where Φ = standard normal CDF
        # 6. Black swan fires where U < 0.05 (same 5% marginal probability,
        #    but now correlated — same-route shipments tend to fail together)
        C = self._build_correlation_matrix(enriched_records)
        L = np.linalg.cholesky(C)                              # (N, N) lower triangular

        Z = np.random.standard_normal(size=(iterations, n))    # iid standard normals
        corr_Z = (L @ Z.T).T                                   # correlated normals (I, N)
        corr_U = _norm.cdf(corr_Z)                             # uniform [0,1] with copula structure
        black_swan_mask = corr_U < 0.05                        # 5% marginal, now correlated

        pareto_raw   = np.random.pareto(1.5, size=(iterations, n)) * base_delays
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
        # Apply grace period per shipment before penalty math.
        # effective_delays[i,j] = max(0, sim_delays[i,j] - grace_days[j])
        # Mirrors SLAPenaltyModel.compute(): penalties only clock after grace expires.
        effective_delays = np.maximum(0.0, sim_delays - grace_days[np.newaxis, :])

        # Shape broadcast: effective_delays (I×N) × daily_rates (N,) × order_values (N,)
        sim_sla_raw = effective_delays * daily_rates[np.newaxis, :] * order_values[np.newaxis, :]
        sim_sla     = np.minimum(sim_sla_raw, sla_caps[np.newaxis, :])

        # --- Full ReVM simulation: all 5 cost components ---
        sim_revm_matrix    = base_profits - risk_penalties - time_costs - fx_costs - sim_sla
        simulated_outcomes = np.sum(sim_revm_matrix, axis=1)

        var_95     = np.percentile(simulated_outcomes, 5)
        worst_case = np.min(simulated_outcomes)

        # Compute baseline SLA total with grace applied (consistent with sla_model.py)
        baseline_effective_delays = np.maximum(0.0, base_delays - grace_days)
        baseline_sla_total = float(np.sum(
            np.minimum(baseline_effective_delays * daily_rates * order_values, sla_caps)
        ))

        return {
            "baseline_revm":               round(baseline_total_revm, 2),
            "var_95":                      round(var_95, 2),           # shorthand alias
            "stochastic_var_floor_95pct":  round(var_95, 2),           # backward compat
            "absolute_maximum_loss_floor": round(worst_case, 2),
            "simulations_executed_cycles": iterations,
            "distribution_model": (
                f"Log-Normal costs (CV=30%) | Poisson base delays (independent) | "
                f"Pareto Black Swan (5%, capped {MAX_BLACK_SWAN_DELAY_DAYS}d, "
                f"Gaussian copula correlated by route) | "
                f"SLA grace-adjusted + re-computed under stress"
            ),
            "baseline_sla_total":          round(baseline_sla_total, 2),
            "scenarios": [round(float(x), 2) for x in simulated_outcomes[:20]],
        }
