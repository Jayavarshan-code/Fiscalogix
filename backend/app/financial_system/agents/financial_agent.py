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

        # Read risk outputs from RiskAgent result — purely functional, no row reads.
        # Falls back to per-row value (or 0.05) only if RiskAgent failed.
        risk_result  = prior_results.get("RiskAgent")
        prior_risk   = (
            risk_result.data.get("risk_outputs", [])
            if (risk_result and risk_result.success)
            else []
        )

        # Batch compute cost components
        fx_outputs  = self._fx.compute_batch(enriched_data, predicted_delays)
        sla_outputs = self._sla.compute_batch(enriched_data, predicted_delays)

        total_revm     = 0.0
        row_enrichments: list = []

        for i, row in enumerate(enriched_data):
            contribution_profit = row.get("contribution_profit", 0.0)
            order_value         = row.get("order_value", 0.0)

            # Risk score: prefer RiskAgent result; fallback to row value or 0.05
            risk_score = (
                prior_risk[i]["score"]
                if i < len(prior_risk)
                else row.get("risk_score", 0.05)
            )

            risk_penalty = risk_score * order_value
            time_cost    = self._time.compute(row, predicted_delays[i], tenant_id=tenant_id)

            clv_calibration = row.get("clv_calibration")
            future_result   = self._future.compute(
                row, predicted_delays[i], row.get("predicted_demand", 0),
                clv_calibration=clv_calibration,
            )

            if isinstance(future_result, dict):
                future_cost = future_result["value"]
                clv_fields  = {
                    "clv_multiplier":    future_result.get("clv_multiplier"),
                    "clv_source":        future_result.get("clv_source"),
                    "churn_probability": future_result.get("churn_probability"),
                    "clv_at_risk":       future_result.get("clv_at_risk"),
                }
            else:
                future_cost = float(future_result)
                clv_fields  = {}

            fx_cost     = fx_outputs[i]
            sla_penalty = sla_outputs[i]
            gst_cost    = row.get("gst_cost", 0.0)

            revm = (
                contribution_profit
                - risk_penalty - time_cost - future_cost
                - fx_cost - sla_penalty - gst_cost
            )
            total_revm += revm

            # Collect enrichments — fan-in in AgentExecutionStage applies these to rows.
            row_enrichments.append({
                "risk_penalty": risk_penalty,
                "time_cost":    time_cost,
                "future_cost":  future_cost,
                "fx_cost":      fx_cost,
                "sla_penalty":  sla_penalty,
                "gst_cost":     gst_cost,
                "revm":         revm,
                **clv_fields,
            })

        # Aggregated portfolio summary
        summary        = self._aggregator.summarize(enriched_data)
        cashflow_report = self._cashflow.run(enriched_data)
        ending_cash    = cashflow_report.get("cash_position", {}).get("ending_cash", 50_000.0)

        # Monte Carlo VaR — run only on portfolio with risk exposure
        var_output = self._mc.simulate_var(enriched_data, 1000)

        return {
            "summary":         summary,
            "cashflow":        cashflow_report,
            "var":             var_output,
            "total_revm":      round(total_revm, 2),
            "ending_cash":     ending_cash,
            "var_95":          var_output.get("var_95", 0),
            "peak_deficit":    cashflow_report.get("metrics", {}).get("peak_deficit", 0),
            "row_enrichments": row_enrichments,
        }
