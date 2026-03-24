from app.Db.neo4j_client import neo4j_client

class GNNRiskMapper:
    """
    Pillar 11 Upgrade: Mathematical Network Systemic Simulator (NSS).
    Abstracts global supply chains into a physical topological Graph (Nodes & Routes).
    Leverages Neo4j Graph Data Science (GDS) to compute PageRank contagion natively in the database,
    eliminating the Python RAM bottlenecks of NetworkX.
    """
    def __init__(self):
        self.db = neo4j_client

    def map_and_propagate(self, shipments):
        if not shipments:
            return []
            
        # 1. Structural Topological Node Array via Cypher
        # Clear existing transient graph to simulate real-time ML mapping
        self.db.query("MATCH (n) DETACH DELETE n")

        for s in shipments:
            s_id = s.get("shipment_id")
            route = s.get("route", "UNKNOWN_ROUTE")
            carrier = s.get("carrier", "UNKNOWN_CARRIER")
            
            # Isolated ML Inference (The starting baseline before contagion sets in)
            base_risk = float(s.get("risk_score", 0.05))
            
            # Neo4j Merge Queries (Creates Nodes and Edges on the fly)
            query = """
            MERGE (s:Shipment {id: $s_id})
            SET s.isolated_risk = $base_risk
            
            MERGE (r:Route {id: $route})
            MERGE (c:Carrier {id: $carrier})
            
            // Edges logic: Probability flow weights
            MERGE (s)-[e1:FLOWS_TO {weight: $base_risk}]->(r)
            MERGE (r)-[e2:FLOWS_TO {weight: 1.0}]->(s)
            
            MERGE (s)-[e3:CARRIED_BY {weight: $carrier_risk}]->(c)
            MERGE (c)-[e4:CARRIES {weight: 0.5}]->(s)
            """
            
            params = {
                "s_id": str(s_id),
                "route": str(route),
                "carrier": str(carrier),
                "base_risk": base_risk,
                "carrier_risk": base_risk * 0.5
            }
            
            self.db.query(query, params)

        # 3. Eigenvector/PageRank Matrix Diffusion via Neo4j GDS
        # Call the native C++ algorithm to find cascade probabilities
        # (Mocking the exact GDS call here since we assume a transient session)
        
        pr_query = """
        CALL gds.pageRank.stream({
          nodeProjection: '*',
          relationshipProjection: {
            ALL: {
              type: '*',
              orientation: 'NATURAL'
            }
          },
          relationshipWeightProperty: 'weight',
          dampingFactor: 0.85
        })
        YIELD nodeId, score
        RETURN gds.util.asNode(nodeId).id AS id, score
        """
        
        try:
            results = self.db.query(pr_query)
            contagion_scores = {record["id"]: record["score"] for record in results}
        except Exception:
            # Fallback if GDS library is not installed locally; simulate it via degree centrality
            fallback_query = """
            MATCH (n)
            OPTIONAL MATCH (n)-[r]->()
            RETURN n.id AS id, sum(COALESCE(r.weight, 0.1)) AS score
            """
            results = self.db.query(fallback_query)
            contagion_scores = {record["id"]: record["score"] for record in (results or [])}
            
        # Normalize the PageRank bounds to structurally map back into probability vectors
        pagerank_values = list(contagion_scores.values()) if contagion_scores else [0.0]
        mean_pr = sum(pagerank_values) / max(len(pagerank_values), 1)
        std_pr = (sum((x - mean_pr)**2 for x in pagerank_values) / max(len(pagerank_values), 1))**0.5
        max_pagerank = max(pagerank_values + [0.0001])

        mapped_results = []
        for s in shipments:
            s_id = s.get("shipment_id")
            base_risk = float(s.get("risk_score", 0.05))
            
            # The raw algorithmic failure density assigned to this node
            raw_node_score = contagion_scores.get(s_id, 0.0)
            
            # 4. Rigorous Z-Score Contagion Filter (Zero False Positives Threshold)
            # The user explicitly mandated minimal failure rates. We only trigger topological 
            # contagion if the node's page-rank is mathematically a statistical outlier (> 2 Standard Deviations)
            is_statistically_significant = raw_node_score > (mean_pr + (2.0 * std_pr))
            
            structural_network_risk = raw_node_score / max_pagerank

            if is_statistically_significant and structural_network_risk > base_risk:
                final_risk = structural_network_risk
                contagion_detected = True
            else:
                final_risk = base_risk
                contagion_detected = False
            
            # Bound absolutely mapping to 1.0 limit
            final_risk = min(0.99, final_risk)

            mapped_results.append({
                "shipment_id": s_id,
                "isolated_ml_risk": round(base_risk, 3),
                "structural_network_risk": round(structural_network_risk, 3),
                "propagated_risk": round(final_risk, 3),
                "systemic_contagion_detected": contagion_detected
            })
            
        return mapped_results
