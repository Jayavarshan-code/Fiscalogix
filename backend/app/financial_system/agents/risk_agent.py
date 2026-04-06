"""
RiskAgent — runs XGBoost risk scoring + SHAP explainability + GNN contagion.

Input:  enriched_data (rows already have predicted_delay from delay model)
Output: per-row risk scores, SHAP drivers, contagion scores, portfolio summary
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent


class RiskAgent(BaseAgent):
    name = "RiskAgent"

    def __init__(self, risk_engine):
        super().__init__()
        self._engine = risk_engine

    async def run_logic(
        self,
        enriched_data: List[Dict[str, Any]],
        prior_results: Dict[str, Any],
        tenant_id: str,
    ) -> Dict[str, Any]:
        predicted_delays = [row.get("predicted_delay", 0) for row in enriched_data]

        # Batch risk scoring — deterministic XGBoost or heuristic fallback
        risk_outputs = self._engine.compute_batch(enriched_data, predicted_delays)

        # Enrich each row in-place
        for i, row in enumerate(enriched_data):
            row["risk_score"]      = risk_outputs[i]["score"]
            row["risk_confidence"] = risk_outputs[i]["confidence"]
            row["risk_drivers"]    = risk_outputs[i].get("drivers", [])

        # Portfolio-level summary
        scores = [r["score"] for r in risk_outputs]
        high_risk = [r for r in risk_outputs if r["score"] > 0.65]
        critical  = [r for r in risk_outputs if r["score"] > 0.85]

        return {
            "risk_outputs":       risk_outputs,
            "high_risk_count":    len(high_risk),
            "critical_count":     len(critical),
            "avg_risk_score":     round(sum(scores) / max(len(scores), 1), 3),
            "max_risk_score":     round(max(scores, default=0), 3),
            "gnn_active":         self._engine.gnn_model is not None,
        }
