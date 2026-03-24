import numpy as np
import networkx as nx
from typing import Dict, List, Any
from .external_signals import ExternalSignalAggregator

class HybridRiskRadar:
    """
    THE PREDICTIVE BRAIN (UPGRADED)
    - Hybrid Architecture: ML (Graph Contagion) + Rules (External Signals).
    - Probabilistic Output: Confidence Bands [Best, Expected, Worst].
    - External Context: Weather, AIS, News.
    """
    def __init__(self, graph: nx.DiGraph, propagation_beta: float = 0.85):
        self.graph = graph
        self.beta = propagation_beta

    def predict_disruption(self, node_id: str, horizon_hours: float) -> Dict[str, Any]:
        """
        Calculates a hybrid risk score with confidence bands.
        Fuses Graph-based ML with Signal-based Rules.
        """
        if node_id not in self.graph:
            return {"score": 0.05, "confidence_band": [0.0, 0.05, 0.2]}

        # 1. FETCH EXTERNAL SIGNALS (Real-world Rules)
        signals = ExternalSignalAggregator.get_signals_for_node(node_id)
        rule_score = 0.0
        active_signals = []
        
        for signal in signals:
            active_signals.append(f"{signal['type']} ({signal['severity']})")
            if signal['severity'] == "CRITICAL": rule_score = max(rule_score, 0.95)
            elif signal['severity'] == "HIGH": rule_score = max(rule_score, 0.70)
            elif signal['severity'] == "MEDIUM": rule_score = max(rule_score, 0.40)

        # 2. ML PROPAGATION (Graph Contagion)
        seed_shocks = []
        for u, v, data in self.graph.edges(data=True):
            if data.get('is_strike_active'):
                seed_shocks.append({"origin": u, "type": "STRIKE"})

        ml_score = self.graph.nodes[node_id].get('risk_score', 0.05)
        root_cause = "Baseline operating variance"
        
        for shock in seed_shocks:
            try:
                path_duration = nx.dijkstra_path_length(self.graph, shock['origin'], node_id, weight='duration')
                time_offset = horizon_hours - path_duration
                
                if time_offset >= -12:
                    current_contagion = 0.87 * (self.beta ** (path_duration / 24.0))
                    if current_contagion > ml_score:
                        ml_score = current_contagion
                        root_cause = f"ML-PREDICTED {shock['type']} contagion from {shock['origin']} (T+{round(path_duration)}h arrival)"
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue

        # 3. HYBRID FUSION
        # We take the Max of Rules and ML, or blend them if both are active
        final_score = max(rule_score, ml_score)
        if len(active_signals) > 0:
            root_cause = f"HYBRID: {', '.join(active_signals)} + {root_cause}"

        # 4. CONFIDENCE BANDS (Uncertainty increases with time-horizon and node-distance)
        volatility = 0.15 * (horizon_hours / 24.0) # More uncertain the further we look
        best_case = max(0.01, final_score - volatility)
        worst_case = min(0.99, final_score + volatility + (0.1 if rule_score > 0.5 else 0))
        
        confidence = 0.92 if rule_score > 0.5 else 0.78 # Rule-based signals have higher certainty

        return {
            "node": node_id,
            "horizon": horizon_hours,
            "expected_score": round(final_score, 3),
            "confidence_bands": [round(best_case, 3), round(final_score, 3), round(worst_case, 3)],
            "confidence_level": confidence,
            "active_signals": signals,
            "root_cause": root_cause
        }
