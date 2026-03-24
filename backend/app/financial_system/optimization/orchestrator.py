from app.financial_system.optimization.action_generator import CandidateActionGenerator
from app.financial_system.optimization.action_simulator import ActionSimulator
from app.financial_system.optimization.mip_optimizer import MIPOptimizer

class ProfitOptimizationOrchestrator:
    def __init__(self, risk, time, future):
        """
        Receives active instances of REVM Core ML Models logically injecting them into Simulators.
        Upgraded from Greedy to Operations Research (MIP) level mathematics.
        """
        self.generator = CandidateActionGenerator()
        self.simulator = ActionSimulator(risk, time, future)
        
    def optimize(self, enriched_records, available_liquidity):
        """
        Coordinates the highest intelligence flow to definitively resolve optimal constraint-bound Action Sets.
        Now leverages Google OR-Tools SCIP backend for global Mixed-Integer maximums.
        """
        or_tools_solver = MIPOptimizer()
        
        # 1. Generate multi-branch realities and computationally determine strict value
        candidate_matrix = []
        for row in enriched_records:
            branches = self.generator.generate(row)
            for b in branches:
                b["simulated_revm"] = self.simulator.simulate(b)
            candidate_matrix.append(branches)
            
        # 2. Command pure Mathematical Global Solution
        # Instead of heuristically guessing, the MIP calculates the perfect discrete arrangement of elements
        best_decision_set = or_tools_solver.optimize(candidate_matrix, available_cash=available_liquidity)
        
        total_revm_retained = sum(d["expected_revm"] for d in best_decision_set)
        
        return {
            "solver": "Google OR-Tools SCIP Backend (Mixed-Integer Programming)",
            "optimized_decisions": best_decision_set,
            "expected_improvement": {
                "revm_retained_usd": round(total_revm_retained, 2),
                "absolute_optimization": True
            }
        }
