from typing import Dict, List, Any
import numpy as np

class UniversalEFIEngine:
    """
    Pillar Alignment: The "Universal Formula" for Decision Intelligence.
    Implementation of: EFI = Σ P_i * (R_i - C_i - D_i - L_i) - λ * CVaR_α
    """
    
    @staticmethod
    def calculate_efi(
        revenue_scenarios: List[float],
        cost_scenarios: List[float],
        delay_penalty_scenarios: List[float],
        loss_factor_scenarios: List[float],
        holding_cost_scenarios: List[float] = None, # New: Cost of inventory capital
        opportunity_cost_scenarios: List[float] = None, # New: Lost sales due to stockout
        breakdown: Dict[str, Any] = None,
        risk_aversion_lambda: float = 1.0,
        alpha: float = 0.1,
        discount_rate: float = 0.0,
        time_t: float = 0.0,
        fidelity_score: float = 1.0 # New: Data Integrity Score (0.0 to 1.0)
    ) -> Dict[str, Any]:
        """
        Calculates the hardened EFI score based on N simulated scenarios.
        Supports full-spectrum costs: Transport + Inventory + Opportunity.
        """
        # --- Vectorized Matrix Arithmetic ---
        rev = np.array(revenue_scenarios)
        cost = np.array(cost_scenarios)
        pen = np.array(delay_penalty_scenarios)
        loss = np.array(loss_factor_scenarios)
        
        # New Feature: Inventory Holding & Opportunity Costs
        hold = np.array(holding_cost_scenarios) if holding_cost_scenarios is not None else np.zeros_like(rev)
        opp = np.array(opportunity_cost_scenarios) if opportunity_cost_scenarios is not None else np.zeros_like(rev)
        
        num_scenarios = len(rev)
        if num_scenarios == 0: return {"efi_total": 0, "confidence": 0}

        # Compute V_i for all scenarios: Max-Standard Comprehensive Formula
        outcomes = rev - cost - pen - loss - hold - opp
        if discount_rate > 0 and time_t > 0:
            outcomes = outcomes / ((1 + discount_rate) ** time_t)

        # 2. Risk Adjustment (CVaR)
        # Sort and take the bottom alpha%
        n_worst = max(1, int(num_scenarios * alpha))
        sorted_outcomes = np.sort(outcomes)
        worst_cases = sorted_outcomes[:n_worst]
        cvar = float(np.mean(worst_cases))
        
        # 3. Final EFI Score (Expectation - Lambda * |CVaR|)
        expected_v = float(np.mean(outcomes))
        final_efi = expected_v - (risk_aversion_lambda * abs(min(0, cvar)))

        # 4. Confidence Score (1 - (σ / |EFI|)) - Penalized by Data Fidelity
        std_dev = float(np.std(outcomes))
        abs_efi = abs(final_efi)
        
        # Base confidence from statistical variance
        raw_confidence = 1 - (std_dev / abs_efi) if abs_efi > 0 else 0.5
        
        # Final confidence: Weighted by data integrity (The "Anti-Hallucination" Factor)
        # We penalize up to 50% of the confidence if fidelity is 0.0
        fidelity_penalty = (1.0 - fidelity_score) * 0.5
        confidence = max(0.01, min(0.99, raw_confidence - fidelity_penalty))

        # 5. Summarize Granular Breakdown (Vectorized)
        avg_breakdown = {}
        if breakdown:
            for category, sub_components in breakdown.items():
                avg_breakdown[category] = {
                    k: round(float(np.mean(v)), 2) for k, v in sub_components.items()
                }

        return {
            "efi_total": round(final_efi, 2),
            "expected_outcome": round(expected_v, 2),
            "cvar_shortfall": round(cvar, 2),
            "confidence_score": round(confidence, 3),
            "data_fidelity": round(fidelity_score, 2), # New
            "std_dev": round(std_dev, 2),
            "components": {
                "avg_revenue": round(float(np.mean(rev)), 2),
                "avg_cost": round(float(np.mean(cost)), 2),
                "avg_penalty": round(float(np.mean(pen)), 2),
                "avg_loss": round(float(np.mean(loss)), 2)
            },
            "granular_breakdown": avg_breakdown,
            "performance": "Hardware_Accelerated"
        }
