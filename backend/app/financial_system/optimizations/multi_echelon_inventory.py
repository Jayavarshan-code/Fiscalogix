import math
import scipy.stats as st
from typing import Dict, List, Any

class MEIOEngine:
    @staticmethod
    def optimize(
        nodes: List[Dict[str, Any]],
        service_level: float = 0.95
    ) -> List[Dict[str, Any]]:
        """
        Calculates mathematically optimal Safety Stock across the network.
        Uses Stochastic formulas (Lead Time Variance * Demand Variance).
        """
        z_score = st.norm.ppf(service_level)
        optimized_inventory = []
        
        for node in nodes:
            avg_lead_time = node.get("avg_lead_time_days", 14)
            std_dev_lead_time = node.get("std_dev_lead_time", 2)
            avg_daily_demand = node.get("avg_daily_demand", 100)
            std_dev_demand = node.get("std_dev_demand", 15)
            
            variance_demand = std_dev_demand ** 2
            variance_lead_time = std_dev_lead_time ** 2
            
            term1 = avg_lead_time * variance_demand
            term2 = (avg_daily_demand ** 2) * variance_lead_time
            
            safety_stock = z_score * math.sqrt(term1 + term2)
            
            order_quantity = avg_daily_demand * 7
            cycle_stock = order_quantity / 2
            
            optimized_inventory.append({
                "node_id": node.get("node_id"),
                "optimal_safety_stock": math.ceil(safety_stock),
                "optimal_total_inventory": math.ceil(cycle_stock + safety_stock),
                "z_score_used": round(z_score, 3)
            })
            
        return optimized_inventory
