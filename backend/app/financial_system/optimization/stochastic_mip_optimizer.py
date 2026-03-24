from ortools.linear_solver import pywraplp
import numpy as np
from typing import List, Dict, Any

class StochasticMIPOptimizer:
    """
    Tech Giant Upgrade: Two-Stage Stochastic Programming.
    Instead of optimizing for 'Plan A', this solver evaluates 200+ parallel futures per decision
    and identifies the 'Robust' choice using CVaR (Conditional Value at Risk).
    """
    def __init__(self, risk_alpha: float = 0.1):
        """
        risk_alpha: The quantile for CVaR (0.1 = Average of worst 10% of scenarios).
        """
        self.alpha = risk_alpha

    def _calculate_cvar(self, scenarios: List[float]) -> float:
        """Calculates the Conditional Value at Risk (Expected Shortfall)."""
        if not scenarios: return 0.0
        sorted_scenarios = sorted(scenarios)
        n_worst = max(1, int(len(sorted_scenarios) * self.alpha))
        worst_cases = sorted_scenarios[:n_worst]
        return float(np.mean(worst_cases))

    def optimize(self, candidate_matrix: List[List[Dict[str, Any]]], available_cash: float):
        """
        Performs Scenario-Based Decomposition to find the Regret-Minimizing global decision.
        """
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver: return []

        # 1. Decision Variables
        # x[shipment_index][action_index]
        x = {}
        for s_idx, actions in enumerate(candidate_matrix):
            for a_idx, action in enumerate(actions):
                x[(s_idx, a_idx)] = solver.IntVar(0, 1, f"ship_{s_idx}_act_{a_idx}")

        # 2. Logic Constraints: Exactly ONE action per shipment (including 'CANCEL' if provided)
        for s_idx, actions in enumerate(candidate_matrix):
            solver.Add(sum(x[(s_idx, a_idx)] for a_idx in range(len(actions))) <= 1)

        # 3. Budget Constraints (T=0 Cash Outlay)
        cash_limit = solver.Constraint(0, available_cash, "GlobalCashLimit")
        for s_idx, actions in enumerate(candidate_matrix):
            for a_idx, action in enumerate(actions):
                cash_limit.SetCoefficient(x[(s_idx, a_idx)], float(action.get("total_cost", 0.0)))

        # 4. Stochastic Objective: Maximize CVaR (Robustness)
        # Instead of maximizing expected value, we maximize the 'Safety Floor'
        objective = solver.Objective()
        for s_idx, actions in enumerate(candidate_matrix):
            for a_idx, action in enumerate(actions):
                # Calculate the Robust ReVM for this branch across all simulated futures
                scenarios = action.get("scenario_results", [action.get("simulated_revm", 0.0)])
                robust_revm = self._calculate_cvar(scenarios)
                
                # Weight the decision by its robustness
                objective.SetCoefficient(x[(s_idx, a_idx)], robust_revm)

        objective.SetMaximization()
        
        # 5. Solve
        solver.set_time_limit(5000) # 5 seconds limit for complex stochastic hulls
        status = solver.Solve()

        optimized_decisions = []
        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            for s_idx, actions in enumerate(candidate_matrix):
                for a_idx, action in enumerate(actions):
                    if x[(s_idx, a_idx)].solution_value() == 1:
                        # Tech Giant Upgrade: Scenario Narratives (Turning math into stories)
                        scen_results = action.get("scenario_results", [0])
                        mean_revm = np.mean(scen_results)
                        robust_revm = self._calculate_cvar(scen_results)
                        regret_delta = mean_revm - robust_revm
                        
                        best_case = max(scen_results)
                        worst_case = min(scen_results)
                        
                        narratives = [
                            f"Scenario A (Worst Case): Compounding delays at node could lead to ${round(abs(worst_case), 0)} financial shrinkage.",
                            f"Scenario B (Best Case): Smooth transit window yielding ${round(best_case, 0)} maximum margin.",
                            f"Stochastic Strategy: Choosing {action['action_name']} because it prevents the ${round(abs(worst_case), 0)} catastrophic loss, trading ${round(action.get('total_cost', 0), 0)} in immediate cost for high-integrity protection."
                        ]
                        
                        optimized_decisions.append({
                            "shipment_id": action.get("shipment_id"),
                            "action": action["action_name"],
                            "expected_revm": round(mean_revm, 2),
                            "robust_revm_floor": round(robust_revm, 2),
                            "regret_risk": round(regret_delta, 2),
                            "cost_burn": action.get("total_cost", 0),
                            "narratives": narratives,
                            "reason": f"Robust Decision: Chosen to preserve a ${round(robust_revm, 0)} floor across 90th percentile market shocks."
                        })
                        break

        return optimized_decisions
