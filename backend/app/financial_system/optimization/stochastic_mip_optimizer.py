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
                scenarios = action.get("scenario_results", [action.get("simulated_revm", 0.0)])
                # USE THE DYNAMIC ALPHA FOR OBJECTIVE WEIGHTING
                robust_revm = self._calculate_cvar(scenarios, target_alpha)
                objective.SetCoefficient(x[(s_idx, a_idx)], robust_revm)

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
                tight_constraints.append("CASH_LIQUIDITY: >90% budget utilized. Higher ReVM decisions were bypassed due to capital lock.")

        optimized_decisions = []
        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            for s_idx, actions in enumerate(candidate_matrix):
                for a_idx, action in enumerate(actions):
                    if x[(s_idx, a_idx)].solution_value() == 1:
                        scen_results = action.get("scenario_results", [0])
                        mean_revm = np.mean(scen_results)
                        robust_revm = self._calculate_cvar(scen_results, target_alpha)
                        
                        best_case = max(scen_results)
                        worst_case = min(scen_results)
                        
                        # Add Appetite Context to Narratives
                        narratives = [
                            f"Scenario A (Worst Case): Potential ${round(abs(worst_case), 0)} loss in extreme volatility.",
                            f"Stochastic Recommendation: Choosing {action['action_name']} ({risk_appetite} posture) to prioritize a ${round(robust_revm, 0)} safety floor."
                        ]
                        
                        optimized_decisions.append({
                            "shipment_id": action.get("shipment_id"),
                            "action": action["action_name"],
                            "expected_revm": round(mean_revm, 2),
                            "robust_revm_floor": round(robust_revm, 2),
                            "risk_posture": risk_appetite,
                            "narratives": narratives,
                            "tight_constraints": tight_constraints,
                            "reason": f"Resilient Decision: Optimal for {risk_appetite} risk appetite."
                        })
                        break

        return optimized_decisions
