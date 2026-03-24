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

    def add_edge(self, u, v, distance_km, fuel_rate_per_km, crew_rate_per_hour, fixed_fees):
        # Estimated duration (avg 25 km/h for freight)
        duration_hours = distance_km / 25.0
        
        # Operational Costs
        fuel_cost = distance_km * fuel_rate_per_km
        crew_cost = duration_hours * crew_rate_per_hour
        base_op_cost = fuel_cost + crew_cost + fixed_fees
        
        self.graph.add_edge(u, v, 
                           distance=distance_km,
                           duration=duration_hours,
                           base_cost=base_op_cost)

    def sync_gnn_risk(self, gnn_risk_scores: dict):
        """
        Updates the graph with live contagion signals from the GNN Mapper.
        gnn_risk_scores: Mapping of {node_id: float_risk}
        """
        for node, score in gnn_risk_scores.items():
            if node in self.graph:
                self.graph.nodes[node]['risk_score'] = score

    def find_best_route(self, origin, destination):
        """
        Solves for the global optimum path using Risk-Adjusted Expected Value Margin (REVM).
        Weight = BaseCost * (1 + AggregateRisk * Beta)
        """
        def revm_weight(u, v, edge_data):
            u_data = self.graph.nodes[u]
            v_data = self.graph.nodes[v]
            
            # Combine Node Risks (Systemic) and Territory Penalties
            avg_risk = (u_data.get('risk_score', 0.05) + v_data.get('risk_score', 0.05)) / 2
            
            # Geopolitical Multiplier
            # 'Enemy' territory essentially applies a 'Conflict Tax' to the route weight
            geopol_penalty = 0.0
            if u_data.get('territory') == "Enemy" or v_data.get('territory') == "Enemy":
                geopol_penalty = 1.0 # High penalty for conflict zones
            elif u_data.get('territory') == "Neutral":
                geopol_penalty = 0.2
            
            total_risk_factor = avg_risk + geopol_penalty
            
            # Final Risk-Adjusted Cost Weight
            return edge_data['base_cost'] * (1 + (total_risk_factor * self.beta))

        try:
            path = nx.dijkstra_path(self.graph, origin, destination, weight=revm_weight)
            total_cost = nx.dijkstra_path_length(self.graph, origin, destination, weight=revm_weight)
            
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
                "risk_delta_pct": round((total_cost - raw_cost) / raw_cost * 100, 2) if raw_cost > 0 else 0
            }
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
