import time
import numpy as np
from app.financial_system.delay_model import DelayPredictionModel
from app.financial_system.optimization.mip_optimizer import MIPOptimizer

def test_caching():
    print("--- Testing DelayPredictionModel Caching ---")
    model = DelayPredictionModel()
    
    # Create sample data
    data = [{"route": "international", "carrier": "standard", "order_value": 50000} for _ in range(100)]
    
    # First run (Cold)
    t0 = time.time()
    res1 = model.compute_batch(data)
    t1 = time.time()
    lat1 = t1 - t0
    print(f"Cold batch latency (100 rows): {lat1:.4f}s")
    
    # Second run (Warm)
    t0 = time.time()
    res2 = model.compute_batch(data)
    t2 = time.time()
    lat2 = t2 - t0
    print(f"Warm batch latency (100 rows): {lat2:.4f}s")
    
    if lat2 < lat1:
        print(f"✅ SUCCESS: Redis cache reduced ML latency by {((lat1-lat2)/lat1)*100:.1f}%")
    else:
        print("❌ FAILED: Warm latency is not lower than cold latency.")

    print("\n--- Testing MIPOptimizer Caching ---")
    opt = MIPOptimizer()
    candidate_matrix = [[{"shipment_id": "SH-1", "action_name": "SHIP_NOW", "revm": 10000.0, "total_cost": 5000.0, "weight_tons": 5.0}]]
    available_cash = 20000.0
    
    # First run (Cold)
    t0 = time.time()
    opt.optimize(candidate_matrix, available_cash)
    t1 = time.time()
    lat1 = t1 - t0
    print(f"Cold MIP optimization latency: {lat1:.4f}s")
    
    # Second run (Warm)
    t0 = time.time()
    opt.optimize(candidate_matrix, available_cash)
    t2 = time.time()
    lat2 = t2 - t0
    print(f"Warm MIP optimization latency: {lat2:.4f}s")
    
    if lat2 < lat1:
        print(f"✅ SUCCESS: Redis cache reduced MIP latency by {((lat1-lat2)/lat1)*100:.1f}%")
    else:
        print("❌ FAILED: Warm optimization is not faster.")

if __name__ == "__main__":
    test_caching()
