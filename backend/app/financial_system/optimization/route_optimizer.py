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

    def add_edge(self, u, v, distance_km, fuel_rate_per_km, crew_rate_per_hour, fixed_fees, transport_mode="Ocean"):
        # Estimated duration depends on transport mode
        # Ocean: 25 km/h, Rail: 60 km/h, Truck: 80 km/h
        speeds = {"Ocean": 25.0, "Rail": 60.0, "Truck": 80.0}
        avg_speed = speeds.get(transport_mode, 40.0)
        duration_hours = distance_km / avg_speed
        
        # Operational Costs
        fuel_cost = distance_km * fuel_rate_per_km
        # Crew/Driver Cost
        crew_cost = duration_hours * crew_rate_per_hour
        base_op_cost = fuel_cost + crew_cost + fixed_fees
        
        self.graph.add_edge(u, v, 
                           distance=distance_km,
                           duration=duration_hours,
                           base_cost=base_op_cost,
                           mode=transport_mode,
                           is_strike_active=False)

    def set_strike(self, u, v, active=True):
        """Sets a labor strike on a specific logistics link."""
        if self.graph.has_edge(u, v):
            self.graph[u][v]['is_strike_active'] = active

    def find_best_route(self, origin, destination, is_critical=False, risk_engine=None):
        """
        Solves for the global optimum path across multiple tiers (Maritime/Domestic).
        Weight = BaseCost * (1 + AggregateRisk(t=ETA) * Beta * CriticalMultiplier)
        """
        def multimodal_weight(u, v, edge_data):
            u_data = self.graph.nodes[u]
            v_data = self.graph.nodes[v]
            
            # --- Tech Giant Evolution: Temporal Risk Sensing ---
            # Instead of static risk, we estimate the risk AT THE TIME OF ARRIVAL (ETA)
            # For simplicity in Dijkstra, we use the distance from origin as a time heuristic
            try:
                eta_hours = nx.dijkstra_path_length(self.graph, origin, u, weight='duration')
            except:
                eta_hours = 0
                
            node_risk = 0.05
            if risk_engine:
                # Query the future state of the node (T + ETA)
                res = risk_engine.predict_contagion(v, eta_hours + edge_data['duration'])
                node_risk = res['score']
            else:
                node_risk = (u_data.get('risk_score', 0.05) + v_data.get('risk_score', 0.05)) / 2
            
            # Geopolitical/Strike Penalties
            risk_penalty = 0.0
            
            # Logistics Strikes check (Direct)
            if edge_data.get('is_strike_active'):
                risk_penalty = 2.0 if is_critical else 0.5
            
            # Goods Nature Multiplier
            critical_beta = self.beta * (3.0 if is_critical else 1.0)
            
            total_risk_factor = node_risk + risk_penalty
            
            # Final Multimodal Weight
            return edge_data['base_cost'] * (1 + (total_risk_factor * critical_beta))

        try:
            path = nx.dijkstra_path(self.graph, origin, destination, weight=multimodal_weight)
            total_cost = nx.dijkstra_path_length(self.graph, origin, destination, weight=multimodal_weight)
            
            # Extract readable stats for the Decision Engine
            total_distance = sum(self.graph[path[i]][path[i+1]]['distance'] for i in range(len(path)-1))
            total_duration = sum(self.graph[path[i]][path[i+1]]['duration'] for i in range(len(path)-1))
            raw_cost = sum(self.graph[path[i]][path[i+1]]['base_cost'] for i in range(len(path)-1))

            return {
                "route": " -> ".join(path),
                "nodes": path,
                "total_distance_km": round(total_distance, 2),
                "total_duration_hours": round(total_duration, 2),
                "operational_cost_usd": round(raw_cost, 2),
                "risk_adjusted_cost_usd": round(total_cost, 2),
                "risk_delta_pct": round((total_cost - raw_cost) / raw_cost * 100, 2) if raw_cost > 0 else 0,
                "is_critical_goods": is_critical
            }
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
