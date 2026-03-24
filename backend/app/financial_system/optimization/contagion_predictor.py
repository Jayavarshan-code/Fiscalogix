import numpy as np
import networkx as nx
from typing import Dict, List, Any

class TemporalContagionPredictor:
    """
    Advanced Supply Chain Contagion Engine.
    Models the 'Propagation Velocity' of shocks (strikes, congestion, outages) 
    across a multimodal logistics graph.
    """
    def __init__(self, graph: nx.DiGraph, propagation_beta: float = 0.85):
        self.graph = graph
        self.beta = propagation_beta

    def predict_risk_at_time(self, node_id: str, horizon_hours: float) -> Dict[str, Any]:
        """
        Calculates the risk of a node at a specific point in the future.
        Logic: Risk(node, t) = Max(LocalRisk, Sum(NeighborRisk(t - transit_time) * Decay))
        """
        if node_id not in self.graph:
            return {"score": 0.05, "explanation": "Node not found in topology."}

        # 1. Identify active 'Seed Shocks' in the network
        seed_shocks = []
        for u, v, data in self.graph.edges(data=True):
            if data.get('is_strike_active'):
                seed_shocks.append({"origin": u, "target": v, "type": "STRIKE"})

        best_score = self.graph.nodes[node_id].get('risk_score', 0.05)
        root_cause = "Local operating environment"
        confidence = 0.95

        # 2. Simulate Contagion Propagation
        for shock in seed_shocks:
            try:
                # Find shortest path duration from shock origin to current node
                path_duration = nx.dijkstra_path_length(self.graph, shock['origin'], node_id, weight='duration')
                
                # If the shock propagation hasn't reached the node yet at the horizon T
                time_delta = horizon_hours - path_duration
                
                # Propagation Logic: Risk decays over time-distance and graph hops
                # If time_delta > 0, the shock has 'arrived' at the node
                if time_delta >= -12: # Include 12h 'Warning Window'
                    contagion_prob = 0.87 * (self.beta ** (path_duration / 24.0)) # Decay by day
                    
                    if contagion_prob > best_score:
                        best_score = contagion_prob
                        # XAI Capture: Explainable root cause and timing
                        arrival_time = "NOW" if time_delta >= 0 else f"in {abs(round(time_delta))}h"
                        root_cause = f"{shock['type']} contagion from {shock['origin']} (Travel Offset: {round(path_duration)}h). Expected impact {arrival_time}."
                        confidence = 0.85 # Propagated risk has lower confidence than direct risk
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue

        return {
            "node": node_id,
            "horizon_hours": horizon_hours,
            "score": round(best_score, 3),
            "explanation": root_cause,
            "confidence": confidence
        }

    def get_contagion_map(self, horizon_hours: float) -> Dict[str, float]:
        """Provides a global snapshot of the network risk at T+Horizon."""
        return {node: self.predict_risk_at_time(node, horizon_hours)["score"] for node in self.graph.nodes()}
