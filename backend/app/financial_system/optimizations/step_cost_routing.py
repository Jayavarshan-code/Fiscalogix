import pulp
from typing import Dict, List, Any

class StepCostRoutingEngine:
    @staticmethod
    def optimize(
        origins: List[str],
        destinations: List[str],
        supply: Dict[str, int],
        demand: Dict[str, int],
        base_costs: Dict[str, Dict[str, float]],
        discounted_costs: Dict[str, Dict[str, float]],
        volume_thresholds: Dict[str, Dict[str, int]],
        capacities: Dict[str, Dict[str, int]]
    ) -> Dict[str, Any]:
        """
        Solves the network problem with Non-Linear Step Functions (Volume Discounts).
        Uses Binary Integer Constraints (Big-M method) to trigger discounts.
        """
        prob = pulp.LpProblem("Network_Optimization_With_Tariffs", pulp.LpMinimize)
        routes = [(i, j) for i in origins for j in destinations]
        
        route_vars = pulp.LpVariable.dicts("Route", (origins, destinations), lowBound=0, cat='Integer')
        discount_triggers = pulp.LpVariable.dicts("DiscountTrigger", (origins, destinations), cat='Binary')
        
        base_vol = pulp.LpVariable.dicts("BaseVol", (origins, destinations), lowBound=0, cat='Integer')
        disc_vol = pulp.LpVariable.dicts("DiscVol", (origins, destinations), lowBound=0, cat='Integer')
        
        BigM = 1000000 
        
        prob += pulp.lpSum([
            base_vol[i][j] * base_costs[i][j] + disc_vol[i][j] * discounted_costs[i][j] 
            for (i, j) in routes
        ]), "Total_Cost_With_Discounts"
        
        for i in origins:
            for j in destinations:
                threshold = volume_thresholds[i][j]
                
                prob += route_vars[i][j] == base_vol[i][j] + disc_vol[i][j]
                
                prob += disc_vol[i][j] <= BigM * discount_triggers[i][j]
                prob += base_vol[i][j] >= threshold * discount_triggers[i][j]
                prob += base_vol[i][j] <= threshold
                
                prob += route_vars[i][j] <= capacities[i][j]
                
        for i in origins:
            prob += pulp.lpSum([route_vars[i][j] for j in destinations]) <= supply[i]
        for j in destinations:
            prob += pulp.lpSum([route_vars[i][j] for i in origins]) >= demand[j]

        solver = pulp.PULP_CBC_CMD(msg=False)
        status = prob.solve(solver)
        
        optimization_status = pulp.LpStatus[status]
        if optimization_status != "Optimal":
            return {"status": optimization_status, "routing_plan": []}

        routing_plan = []
        for i in origins:
            for j in destinations:
                amt = route_vars[i][j].varValue
                if amt and amt > 0:
                    triggered = bool(discount_triggers[i][j].varValue)
                    effective_cost = (base_vol[i][j].varValue * base_costs[i][j]) + (disc_vol[i][j].varValue * discounted_costs[i][j])
                    routing_plan.append({
                        "origin": i,
                        "destination": j,
                        "quantity": int(amt),
                        "got_volume_discount": triggered,
                        "total_lane_cost": effective_cost
                    })

        return {
            "status": optimization_status,
            "total_cost_usd": pulp.value(prob.objective),
            "routing_plan": routing_plan
        }
