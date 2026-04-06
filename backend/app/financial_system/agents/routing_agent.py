"""
RoutingAgent — geopolitical route optimization + strike/disruption detection.

Only dispatched when the situation context flags active disruptions.
Calls Dijkstra-based route optimizer and syncs GNN contagion signals.
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent


class RoutingAgent(BaseAgent):
    name = "RoutingAgent"

    def __init__(self, route_optimizer, poe):
        super().__init__()
        self._optimizer = route_optimizer
        self._poe       = poe

    async def run_logic(
        self,
        enriched_data: List[Dict[str, Any]],
        prior_results: Dict[str, Any],
        tenant_id: str,
    ) -> Dict[str, Any]:
        # Sync GNN risk signals into the geopolitical graph
        risk_results = prior_results.get("RiskAgent")
        if risk_results and risk_results.success:
            gnn_mapping = {}
            for i, row in enumerate(enriched_data):
                sid = row.get("shipment_id")
                if sid:
                    gnn_mapping[sid] = row.get("risk_score", 0.05)
                route_prefix = str(row.get("route", "")).split("-")[0]
                if route_prefix:
                    gnn_mapping[route_prefix] = row.get("risk_score", 0.05)
            self._optimizer.sync_gnn_risk(gnn_mapping)

        # Detect active disruptions from graph state
        active_disruptions = self._detect_disruptions()

        # Run profit optimization engine — returns recommended actions per shipment
        financial_results = prior_results.get("FinancialAgent")
        ending_cash = (
            financial_results.data.get("ending_cash", 50_000.0)
            if financial_results and financial_results.success
            else 50_000.0
        )
        optimization_payload = self._poe.optimize(enriched_data, ending_cash)

        return {
            "active_disruptions":    active_disruptions,
            "disruption_count":      len(active_disruptions),
            "optimization_payload":  optimization_payload,
            "recommendations":       [
                p.get("action") for p in optimization_payload if p.get("action")
            ],
        }

    def _detect_disruptions(self) -> List[str]:
        """
        Reads strike and congestion flags from the geopolitical graph.
        Returns list of human-readable disruption descriptions.
        """
        disruptions = []
        try:
            graph = self._optimizer.graph
            for u, v, data in graph.edges(data=True):
                if data.get("strike_active"):
                    disruptions.append(f"Labor strike active: {u} → {v}")
                if data.get("congestion_index", 0) > 0.7:
                    disruptions.append(f"High congestion: {u} → {v} ({data['congestion_index']:.0%})")
            for node, data in graph.nodes(data=True):
                if data.get("territory_type") == "Enemy":
                    disruptions.append(f"Conflict zone in routing path: {node}")
        except Exception as e:
            self.logger.warning(f"RoutingAgent._detect_disruptions: {e}")
        return disruptions
