class ImpactEngine:
    """
    Translates raw algorithmic metrics (WACC, REVM, stochastic VaR) 
    into plain-English CFO-ready financial impacts.
    """
    def compute(self, enriched_records, optimization_payload, stochastic_var):
        if not enriched_records:
            return {}

        # 1. Calculate the Unlocked Working Capital (UWC)
        # This is the trapped capital that Fiscalogix can technically free up 
        # by executing the optimization recommendations.
        baseline_cost = sum(r.get("total_cost", 0) for r in enriched_records)
        optimized_savings = optimization_payload.get("projected_savings", 0.0)
        
        # New Metric: Prevented SLA Fines (Contractual Protection)
        preventable_sla_fines = sum(r.get("sla_penalty", 0.0) for r in enriched_records)
        
        # Unlocked capital is savings + reduction in risk exposure
        current_risk_exposure = abs(stochastic_var.get("stochastic_var_95_revm", 0.0))
        # Assuming the system mitigates 40% of the 95% Confidence VaR exposure
        risk_savings = current_risk_exposure * 0.40
        
        unlocked_working_capital = optimized_savings + risk_savings + preventable_sla_fines
        
        # 2. Annualized Flow (Scaling the snapshot to a yearly view)
        # Assume the current data represents 1 month of operations for the narrative
        annualized_savings = unlocked_working_capital * 12

        # 3. Generate CFO Narrative
        narrative = (
            f"By executing Fiscalogix recommendations, you instantly avoid ${preventable_sla_fines:,.2f} in contractual OTIF late fines. "
            f"This unlocks ${unlocked_working_capital:,.2f} in total working capital this period. "
            f"Annualized, this drives ${annualized_savings:,.2f} in free cash flow back to your balance sheet, directly mitigating a 95% VaR exposure of ${current_risk_exposure:,.2f}."
        )

        return {
            "unlocked_working_capital": round(unlocked_working_capital, 2),
            "annualized_savings": round(annualized_savings, 2),
            "risk_exposure_mitigated": round(risk_savings, 2),
            "sla_penalties_avoided": round(preventable_sla_fines, 2),
            "cfo_narrative": narrative
        }
