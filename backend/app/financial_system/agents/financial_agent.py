"""
FinancialAgent — computes ReVM, FX costs, SLA penalties, time value, and Monte Carlo VaR.

Reads risk scores from RiskAgent output (must run after RiskAgent).
All numbers are deterministic — this agent never calls the LLM.
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent


class FinancialAgent(BaseAgent):
    name = "FinancialAgent"

    def __init__(self, time_model, future_model, fx_model, sla_model,
                 aggregator, monte_carlo, cashflow):
        super().__init__()
        self._time       = time_model
        self._future     = future_model
        self._fx         = fx_model
        self._sla        = sla_model
        self._aggregator = aggregator
        self._mc         = monte_carlo
        self._cashflow   = cashflow

    async def run_logic(
        self,
        enriched_data: List[Dict[str, Any]],
        prior_results: Dict[str, Any],
        tenant_id: str,
    ) -> Dict[str, Any]:
        predicted_delays = [row.get("predicted_delay", 0) for row in enriched_data]

        # Batch compute cost components
        fx_outputs  = self._fx.compute_batch(enriched_data, predicted_delays)
        sla_outputs = self._sla.compute_batch(enriched_data, predicted_delays)

        total_revm = 0.0
        for i, row in enumerate(enriched_data):
            contribution_profit = row.get("contribution_profit", 0.0)
            order_value         = row.get("order_value", 0.0)
            risk_score          = row.get("risk_score", 0.05)

            risk_penalty = risk_score * order_value
            time_cost    = self._time.compute(row, predicted_delays[i], tenant_id=tenant_id)

            # Gap-7: pass per-account CLV calibration from orchestrator Step 2
            clv_calibration = row.get("clv_calibration")  # None if no history
            future_result   = self._future.compute(
                row, predicted_delays[i], row.get("predicted_demand", 0),
                clv_calibration=clv_calibration,
            )
            # future_model now returns a dict; extract scalar for ReVM formula
            if isinstance(future_result, dict):
                future_cost = future_result["value"]
                # Stamp enriched CLV fields onto row for CFO brief + anomaly detection
                row["clv_multiplier"]    = future_result.get("clv_multiplier")
                row["clv_source"]        = future_result.get("clv_source")
                row["churn_probability"] = future_result.get("churn_probability")
                row["clv_at_risk"]       = future_result.get("clv_at_risk")
            else:
                future_cost = float(future_result)  # backwards compat if called directly

            fx_cost      = fx_outputs[i]
            sla_penalty  = sla_outputs[i]

            revm = contribution_profit - risk_penalty - time_cost - future_cost - fx_cost - sla_penalty

            row.update({
                "risk_penalty": risk_penalty,
                "time_cost":    time_cost,
                "future_cost":  future_cost,
                "fx_cost":      fx_cost,
                "sla_penalty":  sla_penalty,
                "revm":         revm,
            })
            total_revm += revm

        # Aggregated portfolio summary
        summary        = self._aggregator.summarize(enriched_data)
        cashflow_report = self._cashflow.run(enriched_data)
        ending_cash    = cashflow_report.get("cash_position", {}).get("ending_cash", 50_000.0)

        # Monte Carlo VaR — run only on portfolio with risk exposure
        var_output = self._mc.simulate_var(enriched_data, 1000)

        return {
            "summary":        summary,
            "cashflow":       cashflow_report,
            "var":            var_output,
            "total_revm":     round(total_revm, 2),
            "ending_cash":    ending_cash,
            "var_95":         var_output.get("var_95", 0),
            "peak_deficit":   cashflow_report.get("metrics", {}).get("peak_deficit", 0),
        }
