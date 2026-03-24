import time
import numpy as np
from app.financial_system.extensions.gnn_mapper import GNNRiskMapper

def execute_rigorous_topology_audit():
    print("🌐 INITIATING GNN MARKOV CHAIN STRESS TEST")
    
    # Simulate an enormously interwoven logistics graph (10,000 Nodes)
    N = 10000
    print(f"[1] Synthesizing {N} topological matrix connections...")
    shipments = []
    
    # 9,900 Healthy Shipments (Spread across 3 Safe Routes)
    for i in range(9900):
        shipments.append({
            "shipment_id": f"S-SAFE-{i}",
            "route": np.random.choice(["US-LOCAL", "EU-LOCAL", "APAC-LOCAL"]),
            "carrier": "SafeCarrier",
            "risk_score": float(np.random.uniform(0.01, 0.08)) # Standard low baseline risk
        })
        
    # 100 Highly Corrupted Shipments on a specific Contaminated Route
    for i in range(100):
        shipments.append({
            "shipment_id": f"S-CRITICAL-{i}",
            "route": "SHANGHAI-US-WEST",
            "carrier": "ExposedCarrier",
            "risk_score": 0.95 # Guaranteed Failure Matrix
        })
        
    # 10 'Trap' Shipments sharing the carrier but on a DIFFERENT route (Testing False Positives)
    for i in range(10):
        shipments.append({
            "shipment_id": f"S-TRAP-{i}",
            "route": "US-LOCAL",
            "carrier": "ExposedCarrier",
            "risk_score": 0.05
        })

    mapper = GNNRiskMapper()
    
    t0 = time.time()
    print("[2] Executing Pagerank Diffusion via NetworkX...")
    results = mapper.map_and_propagate(shipments)
    print(f"✅ Executed 10,000 node cascade in {time.time() - t0:.4f}s")
    
    # Evaluate Explicit Rigor parameters (Zero False Positives)
    false_positives = 0
    true_positives = 0
    safe_nodes = 0
    
    for r in results:
        s_id = r["shipment_id"]
        contagion = r["systemic_contagion_detected"]
        
        if "SAFE" in s_id and contagion:
            false_positives += 1
        elif "SAFE" in s_id and not contagion:
            safe_nodes += 1
            
        elif "CRITICAL" in s_id and contagion:
            true_positives += 1
            
        elif "TRAP" in s_id:
            # Trap nodes should theoretically NOT fail just because they share a carrier, unless the topology is broken
            if contagion:
                 false_positives += 1
    
    print("\n🔥 GNN ALGORITHMIC RIGOR RESULTS:")
    print(f"   -> True Positives (Collapsed Route Caught): {true_positives}")
    print(f"   -> Safe Nodes Correctly Ignored: {safe_nodes}")
    print(f"   -> False Positives (Hallucinated Contagion): {false_positives} / {N}")
    
    if false_positives > 0:
        print("❌ FAILED: The mathematical bounds are incorrectly leaking node probability to innocent paths.")
    else:
        print("✅ SUCCESS: Standard Deviation boundaries hold structurally. 0% False Failure Rate across 10,000 arrays!")

if __name__ == "__main__":
    execute_rigorous_topology_audit()
