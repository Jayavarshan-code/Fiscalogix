class ImpactEngine:
    """
    Translates raw algorithmic metrics (WACC, REVM, stochastic VaR)
    into plain-English CFO-ready financial impacts.

    Amounts in the CFO narrative are shown in the tenant's display currency
    (default INR). Pass tenant_id to enable currency formatting; omit for USD.
    """
    def compute(self, enriched_records, optimization_payload, stochastic_var,
                tenant_id: str = "default_tenant"):
        if not enriched_records:
            return {}

        # 1. Calculate the Unlocked Working Capital (UWC)
        # This is the trapped capital that Fiscalogix can technically free up 
        # by executing the optimization recommendations.
        optimized_savings = optimization_payload.get("projected_savings", 0.0)
        
        # New Metric: Prevented SLA Fines (Contractual Protection)
        preventable_sla_fines = sum(r.get("sla_penalty", 0.0) for r in enriched_records)

        # P2-F FIX: wrong key + guard against list being passed instead of dict.
        # monte_carlo returns "var_95" (alias "stochastic_var_floor_95pct"), not
        # "stochastic_var_95_revm". Also, some callers pass the raw list of scenarios
        # rather than the full dict — guard with isinstance to avoid AttributeError.
        _var_dict = stochastic_var if isinstance(stochastic_var, dict) else {}
        current_risk_exposure = abs(
            _var_dict.get("var_95", _var_dict.get("stochastic_var_floor_95pct", 0.0))
        )
        # Assuming the system mitigates 40% of the 95% Confidence VaR exposure
        risk_savings = current_risk_exposure * 0.40
        
        unlocked_working_capital = optimized_savings + risk_savings + preventable_sla_fines
        
        # 2. Annualized Flow (Scaling the snapshot to a yearly view)
        # Assume the current data represents 1 month of operations for the narrative
        annualized_savings = unlocked_working_capital * 12

        # 3. Generate CFO Narrative — amounts in tenant's display currency
        try:
            from app.utils.currency import fmt as _fmt
            _f = lambda v: _fmt(v, tenant_id)
        except Exception:
            _f = lambda v: f"${v:,.2f}"   # fallback to USD if currency util unavailable

        narrative = (
            f"By executing Fiscalogix recommendations, you instantly avoid "
            f"{_f(preventable_sla_fines)} in contractual OTIF late fines. "
            f"This unlocks {_f(unlocked_working_capital)} in total working capital this period. "
            f"Annualized, this drives {_f(annualized_savings)} in free cash flow back to your "
            f"balance sheet, directly mitigating a 95% VaR exposure of {_f(current_risk_exposure)}."
        )

        return {
            "unlocked_working_capital": round(unlocked_working_capital, 2),
            "annualized_savings": round(annualized_savings, 2),
            "risk_exposure_mitigated": round(risk_savings, 2),
            "sla_penalties_avoided": round(preventable_sla_fines, 2),
            "cfo_narrative": narrative
        }
