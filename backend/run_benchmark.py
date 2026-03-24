import time
import numpy as np
import json
from app.financial_system.delay_model import DelayPredictionModel
from app.financial_system.optimization.mip_optimizer import MIPOptimizer

def benchmark():
    with open("benchmark_results.txt", "w") as f:
        f.write("--- FISCALOGIX REDIS BENCHMARK ---\n")
        
        # 1. ML Delay Model
        model = DelayPredictionModel()
        data = [{"route": "international", "carrier": "standard", "order_value": 50000} for _ in range(100)]
        
        t0 = time.time()
        model.compute_batch(data)
        lat1 = time.time() - t0
        
        t0 = time.time()
        model.compute_batch(data)
        lat2 = time.time() - t0
        
        f.write(f"ML Delay Model (100 rows):\n")
        f.write(f"  Cold: {lat1:.6f}s\n")
        f.write(f"  Warm: {lat2:.6f}s\n")
        f.write(f"  Improvement: {((lat1-lat2)/lat1)*100:.1f}%\n\n")

        # 2. MIP Optimizer
        opt = MIPOptimizer()
        # Large problem (1000 shipments)
        matrix = [[{"shipment_id": f"SH-{i}", "action_name": "SHIP_NOW", "revm": 10000.0, "total_cost": 5000.0, "weight_tons": 5.0}] for i in range(1000)]
        
        t0 = time.time()
        opt.optimize(matrix, 5000000.0)
        lat1 = time.time() - t0
        
        t0 = time.time()
        opt.optimize(matrix, 5000000.0)
        lat2 = time.time() - t0
        
        f.write(f"OR-Tools MIP Optimizer (1000 items):\n")
        f.write(f"  Cold: {lat1:.6f}s\n")
        f.write(f"  Warm: {lat2:.6f}s\n")
        f.write(f"  Improvement: {((lat1-lat2)/lat1)*100:.1f}%\n\n")

if __name__ == "__main__":
    benchmark()
