import pulp
from typing import Dict, List, Any

class NetworkRoutingEngine:
    @staticmethod
    def optimize(
        origins: List[str],
        destinations: List[str],
        supply: Dict[str, int],
        demand: Dict[str, int],
        costs: Dict[str, Dict[str, float]],
        capacities: Dict[str, Dict[str, int]]
    ) -> Dict[str, Any]:
        """
        Solves the Capacitated Transportation Problem using PuLP.
        Guarantees absolute lowest global cost without violating port capacities.
        """
        prob = pulp.LpProblem("Supply_Chain_Routing_Optimization", pulp.LpMinimize)
        routes = [(i, j) for i in origins for j in destinations]
        
        route_vars = pulp.LpVariable.dicts("Route", (origins, destinations), lowBound=0, cat='Integer')

        prob += pulp.lpSum([route_vars[i][j] * costs[i][j] for (i, j) in routes]), "Total_Routing_Cost"

        for i in origins:
            prob += pulp.lpSum([route_vars[i][j] for j in destinations]) <= supply[i]
        for j in destinations:
            prob += pulp.lpSum([route_vars[i][j] for i in origins]) >= demand[j]
        for i in origins:
            for j in destinations:
                prob += route_vars[i][j] <= capacities[i][j]

        solver = pulp.PULP_CBC_CMD(msg=False)
        status = prob.solve(solver)

        optimization_status = pulp.LpStatus[status]
        if optimization_status != "Optimal":
            return {"status": optimization_status, "total_cost_usd": 0, "routing_plan": []}

        routing_plan = []
        for i in origins:
            for j in destinations:
                shipped_amount = route_vars[i][j].varValue
                if shipped_amount and shipped_amount > 0:
                    routing_plan.append({
                        "origin": i,
                        "destination": j,
                        "quantity": int(shipped_amount),
                        "unit_cost": costs[i][j],
                        "total_lane_cost": shipped_amount * costs[i][j]
                    })

        return {
            "status": optimization_status,
            "total_cost_usd": pulp.value(prob.objective),
            "routing_plan": routing_plan
        }
