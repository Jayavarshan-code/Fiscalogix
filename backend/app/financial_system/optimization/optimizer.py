class GreedyOptimizer:
    def __init__(self, simulator, constraints):
        self.simulator = simulator
        self.constraints = constraints
        
    def solve(self, candidate_matrix):
        """
        Selects the highest-efficiency Master Decision Set mathematically maximizing REVM subject to Constraints.
        candidate_matrix: list of lists (grouped perfectly by shipment)
        """
        scored_actions = []
        
        # 1. Flatten Matrix & Execute Simulator
        for shipment_group in candidate_matrix:
            
            # Find baseline control to isolate objective 'Delta' improvement
            baseline = next((a for a in shipment_group if a["action_name"] == "SHIP_NOW"), shipment_group[0])
            baseline_revm = self.simulator.simulate(baseline)
            baseline["simulated_revm"] = baseline_revm
                
            for action_row in shipment_group:
                sim_revm = self.simulator.simulate(action_row)
                action_row["simulated_revm"] = sim_revm
                
                # Equation: Delta Gain (Value) over Delta Cost (Burn) 💥
                revm_delta = sim_revm - baseline_revm
                cost_delta = action_row.get("total_cost", 0) - baseline.get("total_cost", 0)
                
                # Calculate True Bang-For-Buck Efficiency 
                # Prevents dividing by zero. Favors inherently 'free' value generation heavily.
                if cost_delta > 0:
                    efficiency = revm_delta / cost_delta 
                else:
                    efficiency = revm_delta * 999 if revm_delta > 0 else revm_delta
                
                action_row["revm_delta"] = revm_delta
                action_row["efficiency"] = efficiency
                scored_actions.append(action_row)
                
        # 2. Sort Optimization array by pure mathematical efficiency
        scored_actions.sort(key=lambda x: x["efficiency"], reverse=True)
        
        final_decisions = []
        resolved_shipments = set()
        
        # 3. Greedy Execution loop traversing top-tier efficiencies
        for action in scored_actions:
            s_id = action.get("shipment_id", "UNKNOWN")
            
            if s_id in resolved_shipments:
                continue # Shipment is fully handled by a strictly better mathematical action
                
            # If the best action breaches real cash limits, fallback drops down the array!
            if self.constraints.is_valid(action):
                self.constraints.commit(action)
                resolved_shipments.add(s_id)
                final_decisions.append({
                    "shipment_id": s_id,
                    "action": action["action_name"],
                    "expected_revm": action["simulated_revm"],
                    "revm_delta": round(action["revm_delta"], 2),
                    "reason": f"Optimal constraint-adjusted routing (Efficiency: {round(action['efficiency'], 2)})"
                })
                
        return final_decisions
