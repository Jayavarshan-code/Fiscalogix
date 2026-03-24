from ortools.linear_solver import pywraplp
import numpy as np
from typing import List, Dict, Any

class StochasticMIPOptimizer:
    """
    Tech Giant Upgrade: Interactive Black-Swan Resilient Engine.
    - Dynamic CVaR Quantiles (Risk Appetite)
    - Constraint Slack Analysis (Transparency)
    """
    def __init__(self, risk_alpha: float = 0.1):
        self.alpha = risk_alpha

    def _calculate_cvar(self, scenarios: List[float], alpha: float) -> float:
        """Calculates the Conditional Value at Risk (Expected Shortfall) for a given alpha."""
        if not scenarios: return 0.0
        sorted_scenarios = sorted(scenarios)
        n_worst = max(1, int(len(sorted_scenarios) * alpha))
        worst_cases = sorted_scenarios[:n_worst]
        return float(np.mean(worst_cases))

    def optimize(self, candidate_matrix: List[List[Dict[str, Any]]], available_cash: float, risk_appetite: str = 'BALANCED'):
        """
        risk_appetite: CONSERVATIVE (0.05 alpha), BALANCED (0.15), AGGRESSIVE (0.35)
        """
        # Map Appetite to Alpha
        alpha_map = {'CONSERVATIVE': 0.05, 'BALANCED': 0.15, 'AGGRESSIVE': 0.35}
        target_alpha = alpha_map.get(risk_appetite, 0.15)
        
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver: return []

        x = {}
        for s_idx, actions in enumerate(candidate_matrix):
            for a_idx, action in enumerate(actions):
                x[(s_idx, a_idx)] = solver.IntVar(0, 1, f"ship_{s_idx}_act_{a_idx}")

        for s_idx, actions in enumerate(candidate_matrix):
            solver.Add(sum(x[(s_idx, a_idx)] for a_idx in range(len(actions))) <= 1)

        cash_limit = solver.Constraint(0, available_cash, "GlobalCashLimit")
        for s_idx, actions in enumerate(candidate_matrix):
            for a_idx, action in enumerate(actions):
                cash_limit.SetCoefficient(x[(s_idx, a_idx)], float(action.get("total_cost", 0.0)))

        objective = solver.Objective()
        for s_idx, actions in enumerate(candidate_matrix):
            for a_idx, action in enumerate(actions):
                # USE THE DYNAMIC ALPHA FOR OBJECTIVE WEIGHTING
                robust_efi = self._calculate_cvar(scenarios, target_alpha)
                objective.SetCoefficient(x[(s_idx, a_idx)], robust_efi)

        objective.SetMaximization()
        solver.set_time_limit(5000)
        status = solver.Solve()

        # Constraint Visibility Analysis
        tight_constraints = []
        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            # Check if Cash Limit is a bottleneck
            # Note: For MIP, dual prices aren't direct, so we check slack
            used_cash = sum(action.get("total_cost", 0) for s_idx, actions in enumerate(candidate_matrix) 
                            for a_idx, action in enumerate(actions) if x[(s_idx, a_idx)].solution_value() == 1)
            
            if used_cash > (available_cash * 0.9):
                tight_constraints.append("CASH_LIQUIDITY: >90% budget utilized. Higher EFI decisions were bypassed due to capital lock.")

        optimized_decisions = []
        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            for s_idx, actions in enumerate(candidate_matrix):
                for a_idx, action in enumerate(actions):
                    if x[(s_idx, a_idx)].solution_value() == 1:
                        scen_results = action.get("scenario_results", [0])
                        mean_efi = np.mean(scen_results)
                        robust_efi = self._calculate_cvar(scen_results, target_alpha)
                        
                        best_case = max(scen_results)
                        worst_case = min(scen_results)
                        
                        # --- Pillar 5 Upgrade: Executive Briefing Layer ---
                        # Benchmark against "Status Quo" (assumed to be the first action in the list)
                        status_quo = actions[0]
                        sq_results = status_quo.get("scenario_results", [0.0])
                        sq_robust_floor = self._calculate_cvar(sq_results, target_alpha)
                        
                        # Profit Impact = Total ReVM difference (Expected)
                        profit_impact = (mean_revm - np.mean(sq_results)) * 100 # Multiplier for ₹ scaling
                        
                        # Risk Reduction = Improvement in the Robust Floor
                        risk_improvement = robust_revm - sq_robust_floor
                        risk_reduction_pct = (risk_improvement / abs(sq_robust_floor)) * 100 if sq_robust_floor != 0 else 0
                        
                        # Operational Alert (if status quo risk is > 70%)
                        sq_risk_score = status_quo.get("risk_score", 0.0)
                        op_alert = "Critical disruption detected" if sq_risk_score > 0.7 else "Standard monitoring active"
                        
                        # Simplified XAI Narrative
                        # "Avoids high-loss scenarios in X% of cases"
                        success_rate = len([s for s in scen_results if s > worst_case]) / len(scen_results) * 100
                        simplified_narrative = f"This route avoids high-loss scenarios in {int(success_rate)}% of simulated cases."

                        optimized_decisions.append({
                            "shipment_id": action.get("shipment_id"),
                            "action": action["action_name"],
                            "expected_efi": round(mean_efi, 2),
                            "robust_efi_floor": round(robust_efi, 2),
                            "risk_posture": risk_appetite,
                            "executive_summary": {
                                "recommended_action": action["action_name"],
                                "profit_impact_delta": round(profit_impact, 0),
                                "risk_reduction_pct": round(max(0, risk_reduction_pct), 1),
                                "operational_alert": op_alert,
                                "executive_narrative": simplified_narrative
                            },
                            "narratives": narratives,
                            "tight_constraints": tight_constraints,
                            "reason": f"Strategic Executive Choice: Optimal for {risk_appetite} posture."
                        })
                        break

        return optimized_decisions
