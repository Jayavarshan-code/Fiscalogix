from app.financial_system.optimization.route_optimizer import GeopoliticalRouteOptimizer

db = GeopoliticalRouteOptimizer(risk_aversion_beta=5.0) # High risk-aversion

# 1. Define Supply Chain Topology
# Nodes
db.add_node("SHENZHEN", territory_type="Friendly")
db.add_node("SINGAPORE", territory_type="Friendly")
db.add_node("ADEN_GULF", territory_type="Enemy") # Conflict Zone
db.add_node("SUEZ_CANAL", territory_type="Neutral")
db.add_node("ROTTERDAM", territory_type="Friendly")
db.add_node("CAPE_GOOD_HOPE", territory_type="Friendly") # The alternative route

# Edges (Routes)
# Standard Route: Shenzhen -> Singapore -> Aden -> Suez -> Rotterdam
db.add_edge("SHENZHEN", "SINGAPORE", 2600, 1.2, 50, 500)
db.add_edge("SINGAPORE", "ADEN_GULF", 6000, 1.2, 50, 1000)
db.add_edge("ADEN_GULF", "SUEZ_CANAL", 2500, 1.2, 50, 5000)
db.add_edge("SUEZ_CANAL", "ROTTERDAM", 6000, 1.2, 50, 2000)

# Alternative Route: Singapore -> Cape of Good Hope -> Rotterdam (Avoids Aden/Suez)
db.add_edge("SINGAPORE", "CAPE_GOOD_HOPE", 11000, 1.2, 50, 1500)
db.add_edge("CAPE_GOOD_HOPE", "ROTTERDAM", 11000, 1.2, 50, 1500)

# 2. Run Optimization Before GNN Risk
print("--- [INITIAL SEARCH] ---")
res = db.find_best_route("SHENZHEN", "ROTTERDAM")
if res:
    print(f"Optimal Path: {res['route']}")
    print(f"Operational Cost: ${res['operational_cost_usd']}")
    print(f"Duration: {res['total_duration_hours']} hours")

# 3. Inject GNN Risk Signal (High contagion detected in ADEN_GULF)
db.sync_gnn_risk({"ADEN_GULF": 0.85})

print("\n--- [RISK-AWARE SEARCH (Geopolitical Contagion)] ---")
res_risk = db.find_best_route("SHENZHEN", "ROTTERDAM")
if res_risk:
    print(f"Optimal Path: {res_risk['route']}")
    print(f"Operational Cost: ${res_risk['operational_cost_usd']}")
    print(f"Risk Adjusted Cost: ${res_risk['risk_adjusted_cost_usd']} (REVM Weighted)")
    print(f"Path Shifted to avoid conflict: {'YES' if 'CAPE_GOOD_HOPE' in res_risk['route'] else 'NO'}")
