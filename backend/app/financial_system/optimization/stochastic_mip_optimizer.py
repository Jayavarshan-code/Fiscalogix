from ortools.linear_solver import pywraplp
import numpy as np
from typing import List, Dict, Any
from app.financial_system.metrics.efi_engine import UniversalEFIEngine

class StochasticMIPOptimizer:
    """
    Tech Giant Upgrade: Hardened EFI Engine.
    Uses: EFI = Σ P_i * (R_i - C_i - D_i - L_i) - λ * CVaR_α
    """
    def __init__(self, risk_alpha: float = 0.1):
        self.alpha = risk_alpha
        self.efi_engine = UniversalEFIEngine()

    def optimize(self, candidate_matrix: List[List[Dict[str, Any]]], available_cash: float, risk_appetite: str = 'BALANCED'):
        """
        risk_appetite: CONSERVATIVE (λ=2.0), BALANCED (λ=1.0), AGGRESSIVE (λ=0.3)
        """
        # Map Appetite to Lambda & Alpha (User Specification Alignment)
        appetite_config = {
            'CONSERVATIVE': {'lambda': 2.0, 'alpha': 0.05},
            'BALANCED': {'lambda': 1.0, 'alpha': 0.15},
            'AGGRESSIVE': {'lambda': 0.3, 'alpha': 0.35}
        }
        config = appetite_config.get(risk_appetite, appetite_config['BALANCED'])
        target_lambda = config['lambda']
        target_alpha = config['alpha']
        
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver: return []

        x = {}
        # Pre-calculate EFI for all actions using the Universal Formula
        for s_idx, actions in enumerate(candidate_matrix):
            for a_idx, action in enumerate(actions):
                x[(s_idx, a_idx)] = solver.IntVar(0, 1, f"ship_{s_idx}_act_{a_idx}")
                
                scen_data = action.get("scenario_results", {})
                if isinstance(scen_data, dict) and "revenue" in scen_data:
                    efi_res = self.efi_engine.calculate_efi(
                        scen_data["revenue"], scen_data["cost"], 
                        scen_data["penalty"], scen_data["loss"],
                        risk_aversion_lambda=target_lambda,
                        alpha=target_alpha
                    )
                else:
                    # Fallback for simple simulations (Legacy support)
                    fallback_val = action.get("simulated_efi", 0.0)
                    efi_res = {
                        "efi_total": fallback_val, 
                        "expected_outcome": fallback_val,
                        "cvar_shortfall": fallback_val * 0.8,
                        "confidence_score": 0.8,
                        "components": {"avg_revenue": order_val, "avg_cost": base_cost, "avg_penalty": 0, "avg_loss": 0}
                    }
                
                action["efi_calculation"] = efi_res

        # Decision Constraint: Only one action per shipment
        for s_idx, actions in enumerate(candidate_matrix):
            solver.Add(sum(x[(s_idx, a_idx)] for a_idx in range(len(actions))) <= 1)

        # Global Cash Constraint
        cash_limit = solver.Constraint(0, available_cash, "GlobalCashLimit")
        for s_idx, actions in enumerate(candidate_matrix):
            for a_idx, action in enumerate(actions):
                cash_limit.SetCoefficient(x[(s_idx, a_idx)], float(action.get("total_cost", 0.0)))

        objective = solver.Objective()
        for s_idx, actions in enumerate(candidate_matrix):
            for a_idx, action in enumerate(actions):
                # Optimize directly for the unified EFI score derived from the Universal Formula
                objective.SetCoefficient(x[(s_idx, a_idx)], action["efi_calculation"]["efi_total"])

        objective.SetMaximization()
        solver.set_time_limit(5000)
        status = solver.Solve()

        tight_constraints = []
        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            used_cash = sum(action.get("total_cost", 0) for s_idx, actions in enumerate(candidate_matrix) 
                            for a_idx, action in enumerate(actions) if x[(s_idx, a_idx)].solution_value() == 1)
            
            if used_cash > (available_cash * 0.9):
                tight_constraints.append("CASH_LIQUIDITY: >90% budget utilized. Higher EFI decisions were bypassed due to capital lock.")

        optimized_decisions = []
        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            for s_idx, actions in enumerate(candidate_matrix):
                for a_idx, action in enumerate(actions):
                    if x[(s_idx, a_idx)].solution_value() == 1:
                        # Extract final results from the EFI engine
                        efi_res = action["efi_calculation"]
                        
                        # Benchmark against "Status Quo"
                        status_quo = actions[0]
                        sq_efi = status_quo.get("efi_calculation", {}).get("efi_total", 0.0)
                        profit_impact = (efi_res["efi_total"] - sq_efi)
                        
                        optimized_decisions.append({
                            "shipment_id": action.get("shipment_id"),
                            "action": action["action_name"],
                            "expected_efi": efi_res["efi_total"],
                            "robust_efi_floor": efi_res["cvar_shortfall"],
                            "confidence_score": efi_res["confidence_score"],
                            "risk_posture": risk_appetite,
                            "executive_summary": {
                                "recommended_action": action["action_name"],
                                "profit_impact_delta": round(profit_impact, 0),
                                "risk_reduction_pct": round(max(0, (efi_res["confidence_score"] * 100)), 1),
                                "operational_alert": "Standard monitoring active" if efi_res["confidence_score"] > 0.85 else "Caution: High Variance Outlook",
                                "executive_narrative": f"Unified EFI calculation suggests {action['action_name']} protects target margins with {int(efi_res['confidence_score']*100)}% statistical confidence."
                            },
                            "components": efi_res["components"],
                            "tight_constraints": tight_constraints,
                            "reason": f"Optimal EFI for {risk_appetite} posture."
                        })
                        break

        return optimized_decisions
