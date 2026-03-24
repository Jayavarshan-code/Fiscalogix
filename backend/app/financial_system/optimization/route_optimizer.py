import networkx as nx

class GeopoliticalRouteOptimizer:
    """
    Advanced Route Optimization Engine.
    Integrates Graph Neural Network (GNN) risk signals with operational cost vectors 
    (Fuel, Crew, Logistics Fees) and Geopolitical Territory Status.
    """
    def __init__(self, risk_aversion_beta: float = 2.0):
        self.graph = nx.DiGraph()
        self.beta = risk_aversion_beta # How much we penalize risk vs cost

    def add_node(self, node_id, territory_type="Friendly"):
        """
        territory_type: Friendly, Neutral, Enemy
        """
        self.graph.add_node(node_id, territory=territory_type, risk_score=0.05)

    def add_edge(self, u, v, distance_km, fuel_rate_per_km, crew_rate_per_hour, fixed_fees, transport_mode="Ocean", 
                 carrier_id="GlobalConsolidated", capacity_limit=1000, customs_delay=0.0):
        speeds = {"Ocean": 25.0, "Rail": 60.0, "Truck": 80.0}
        avg_speed = speeds.get(transport_mode, 40.0)
        duration_hours = (distance_km / avg_speed) + customs_delay
        
        fuel_cost = distance_km * fuel_rate_per_km
        crew_cost = duration_hours * crew_rate_per_hour
        base_op_cost = fuel_cost + crew_cost + fixed_fees
        
        self.graph.add_edge(u, v, 
                           distance=distance_km,
                           duration=duration_hours,
                           base_cost=base_op_cost,
                           mode=transport_mode,
                           carrier=carrier_id,
                           capacity=capacity_limit,
                           customs_delay=customs_delay,
                           is_strike_active=False)

    def find_best_route(self, origin, destination, is_critical=False, risk_engine=None):
        def multimodal_weight(u, v, edge_data):
            # Mode Switch Penalty: $200 + 4 hours if mode changes
            # (Note: In pure Dijkstra, 'previous node' context is tricky, 
            # so we heuristic this or use a simple multiplier if multiple modes exist on nodes)
            mode_switch_penalty = 0
            
            # --- Tech Giant Evolution: Temporal Risk Sensing ---
            try:
                eta_hours = nx.dijkstra_path_length(self.graph, origin, u, weight='duration')
            except:
                eta_hours = 0
                
            node_risk = 0.05
            if risk_engine:
                res = risk_engine.predict_disruption(v, eta_hours + edge_data['duration'])
                node_risk = res['expected_score']
            
            risk_penalty = 0.0
            if edge_data.get('is_strike_active'):
                risk_penalty = 2.0 if is_critical else 0.5
            
            critical_beta = self.beta * (3.0 if is_critical else 1.0)
            total_risk_factor = node_risk + risk_penalty
            
            return edge_data['base_cost'] * (1 + (total_risk_factor * critical_beta))

        try:
            path = nx.dijkstra_path(self.graph, origin, destination, weight=multimodal_weight)
            
            # Extract Executable Stats
            breakdown = {"Ocean": 0, "Rail": 0, "Truck": 0, "Handling": 500} # Handling base
            total_duration = 0
            total_distance = 0
            total_customs = 0
            total_mode_switches = 0
            prev_mode = None
            
            for i in range(len(path)-1):
                edge = self.graph[path[i]][path[i+1]]
                mode = edge['mode']
                breakdown[mode] = breakdown.get(mode, 0) + edge['base_cost']
                total_duration += edge['duration']
                total_distance += edge['distance']
                total_customs += edge.get('customs_delay', 0)
                
                if prev_mode and prev_mode != mode:
                    total_mode_switches += 1
                    breakdown["Handling"] += 200 # Mode switch fee
                prev_mode = mode

            raw_cost = sum(breakdown.values())
            
            # Execution Feasibility Score (Tech Giant positioning)
            # Factors: Mode switches, Customs delays, and Aggregate Node Risk
            feasibility = 100 - (total_mode_switches * 5) - (total_customs * 2)
            feasibility = max(10, min(98, feasibility))
            
            risk_level = "LOW"
            if feasibility < 70: risk_level = "HIGH"
            elif feasibility < 85: risk_level = "MEDIUM"

            return {
                "route": " -> ".join(path),
                "nodes": path,
                "feasibility_score": int(feasibility),
                "risk_level": risk_level,
                "total_duration_hours": round(total_duration, 2),
                "operational_cost_usd": round(raw_cost, 2),
                "cost_breakdown": {k: round(v, 2) for k, v in breakdown.items() if v > 0},
                "executable_constraints": {
                    "mode_switches": total_mode_switches,
                    "customs_delays_hours": round(total_customs, 2),
                    "carriers": list(set(self.graph[path[i]][path[i+1]]['carrier'] for i in range(len(path)-1)))
                }
            }
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
