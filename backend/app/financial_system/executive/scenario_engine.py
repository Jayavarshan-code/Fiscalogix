import copy

class ScenarioSimulationEngine:
    """
    Clones base reality to run parallel "What-If" stress tests across four
    independent shock dimensions:

      delay_shift      — additional transit days (carrier failure, port strike)
      demand_shift_pct — fractional change in predicted demand (+/- %)
      fx_shock_pct     — fractional uplift applied to every row's fx_cost
                         (simulates a sudden currency devaluation or hedge miss)
      cost_shock_pct   — fractional uplift applied to total_cost
                         (simulates freight rate spikes, fuel surcharges, re-routing)

    The orchestrator drives named scenarios from a config list; this engine
    is parameter-only and has no knowledge of scenario names.

    International-only flag:
      Some shocks (e.g. Red Sea closure) only affect cross-border routes.
      When `international_only=True`, delay_shift is applied only to rows
      where the route contains "-" (i.e. is a cross-border corridor).
      Domestic shipments are unaffected — matching real-world canal closures.
    """

    def __init__(self, risk_engine, time_model, future_model, cashflow_orchestrator):
        self.risk     = risk_engine
        self.time     = time_model
        self.future   = future_model
        self.cashflow = cashflow_orchestrator

    def simulate(
        self,
        base_records,
        scenario_name,
        delay_shift       = 0,
        demand_shift_pct  = 0.0,
        fx_shock_pct      = 0.0,   # e.g. 0.30 = fx_cost increases 30%
        cost_shock_pct    = 0.0,   # e.g. 0.40 = total_cost increases 40%
        international_only = False, # when True, delay_shift only hits cross-border routes
    ):
        cloned_records = copy.deepcopy(base_records)
        base_revm = sum(r["revm"] for r in base_records)

        for r in cloned_records:
            is_international = "-" in str(r.get("route", ""))

            # ── Delay shock ───────────────────────────────────────────────────
            effective_delay_shift = delay_shift
            if international_only and not is_international:
                effective_delay_shift = 0   # canal closure doesn't affect domestic routes

            r["delay_days"]      = r.get("delay_days", 0) + effective_delay_shift
            # P3-2 FIX: shift the field that cost engines actually read
            r["predicted_delay"] = (
                r.get("predicted_delay", r.get("delay_days", 0)) + effective_delay_shift
            )

            # ── Demand shock ──────────────────────────────────────────────────
            r["predicted_demand"] = r.get("predicted_demand", 0) * (1.0 + demand_shift_pct)

            # ── FX shock — scales the stored fx_cost for the scenario ─────────
            # Models a sudden currency move or hedge programme failure.
            r["fx_cost"] = r.get("fx_cost", 0.0) * (1.0 + fx_shock_pct)

            # ── Cost shock — models freight rate spikes / surcharges ──────────
            # Scales total_cost used by time model holding cost calculation.
            if cost_shock_pct != 0.0:
                r["total_cost"]    = r.get("total_cost", 0.0)    * (1.0 + cost_shock_pct)
                r["shipment_cost"] = r.get("shipment_cost", 0.0) * (1.0 + cost_shock_pct)

            # ── Re-run ReVM cost components under stressed inputs ─────────────
            predicted_delay = r["predicted_delay"]
            risk_output     = self.risk.compute(r, predicted_delay)
            r["risk_score"] = risk_output["score"]
            risk_penalty    = r["risk_score"] * r.get("order_value", 0.0)

            time_cost   = self.time.compute(r, predicted_delay)
            future_cost = self.future.compute(r, predicted_delay, r.get("predicted_demand", 0))

            fx_cost     = r.get("fx_cost", 0.0)      # already shocked above
            sla_penalty = r.get("sla_penalty", 0.0)
            tariff_cost = r.get("tariff_cost", 0.0)  # tariff unchanged by these shocks

            r["revm"] = (
                r.get("contribution_profit", 0.0)
                - risk_penalty
                - time_cost
                - future_cost
                - fx_cost
                - sla_penalty
                - tariff_cost
            )

        # Re-run cashflow pipeline to detect how stress fractures the cash timeline
        new_cashflow  = self.cashflow.run(cloned_records)
        scenario_revm = sum(r["revm"] for r in cloned_records)
        revm_change   = scenario_revm - base_revm

        return {
            "scenario": scenario_name,
            "shocks_applied": {
                "delay_shift_days":    delay_shift,
                "demand_shift_pct":    round(demand_shift_pct * 100, 1),
                "fx_shock_pct":        round(fx_shock_pct * 100, 1),
                "cost_shock_pct":      round(cost_shock_pct * 100, 1),
                "international_only":  international_only,
            },
            "impact": {
                "revm_change":  round(revm_change, 2),
                "peak_deficit": new_cashflow["metrics"]["peak_deficit"],
                "revm_change_pct": round(
                    (revm_change / abs(sum(r["revm"] for r in base_records)) * 100)
                    if base_records else 0, 1
                ),
            },
        }
