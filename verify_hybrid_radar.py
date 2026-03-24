import networkx as nx
from backend.app.financial_system.optimization.contagion_predictor import HybridRiskRadar

def test_hybrid_radar():
    # Build a simple graph: Port_A -> Hub_B (24h) -> Dest_C (24h)
    G = nx.DiGraph()
    G.add_edge("Port_A", "Hub_B", duration=24, is_strike_active=True)
    G.add_edge("Hub_B", "Dest_C", duration=24)
    G.nodes["Port_A"]["risk_score"] = 0.05
    G.nodes["Hub_B"]["risk_score"] = 0.05
    G.nodes["Dest_C"]["risk_score"] = 0.05

    radar = HybridRiskRadar(G)
    
    # CASE 1: T+48h prediction at Destination (Should show ML contagion)
    res = radar.predict_disruption("Dest_C", 48)
    print(f"\n--- Probabilistic Radar (T+48 at Dest_C) ---")
    print(f"Expected Risk: {res['expected_score']}")
    print(f"Confidence Band: {res['confidence_bands']}")
    print(f"Root Cause: {res['root_cause']}")
    
    # CASE 2: External Signal detected at Node
    # (Since ExternalSignalAggregator is random, we'll run it a few times to see logic)
    print(f"\n--- Signal Resilience Test (Randomized) ---")
    for _ in range(5):
        res = radar.predict_disruption("Port_A", 0)
        if len(res['active_signals']) > 0:
            print(f"SIGNAL DETECTED: {res['active_signals'][0]['type']} - Risk elevated to {res['expected_score']}")
        else:
            print("No signal this tick.")

if __name__ == "__main__":
    test_hybrid_radar()
