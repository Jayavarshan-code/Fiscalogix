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
        risk_aversion_lambda: float = 1.0,
        alpha: float = 0.1,
        discount_rate: float = 0.0,
        time_t: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculates the hardened EFI score based on N simulated scenarios.
        """
        num_scenarios = len(revenue_scenarios)
        if num_scenarios == 0: return {"efi_total": 0, "confidence": 0}

        # 1. Compute V_i for each scenario
        outcomes = []
        for i in range(num_scenarios):
            v_i = (revenue_scenarios[i] - 
                   cost_scenarios[i] - 
                   delay_penalty_scenarios[i] - 
                   loss_factor_scenarios[i])
            
            # Time Discounting: V_i / (1 + r)^t
            if discount_rate > 0 and time_t > 0:
                v_i = v_i / ((1 + discount_rate) ** time_t)
            
            outcomes.append(v_i)

        # 2. Risk Adjustment (CVaR)
        sorted_outcomes = sorted(outcomes)
        n_worst = max(1, int(num_scenarios * alpha))
        worst_cases = sorted_outcomes[:n_worst]
        cvar = float(np.mean(worst_cases))
        
        # 3. Final EFI Score (Expectation - Lambda * |CVaR|)
        expected_v = float(np.mean(outcomes))
        # Note: If CVaR is negative (loss), we penalize it. 
        # If it's the 5% worst profit (e.g. $1k), we still use it for shift.
        # Standard approach is to subtract the shortfall from expectation.
        final_efi = expected_v - (risk_aversion_lambda * abs(min(0, cvar)))

        # 4. Confidence Score (1 - Normalized Variance)
        variance = float(np.var(outcomes))
        # Normalize variance by mean squared (Coefficient of Variation squared)
        cv_sq = (variance / (expected_v ** 2)) if expected_v != 0 else 1.0
        confidence = max(0.1, min(0.99, 1 - min(1, cv_sq)))

        return {
            "efi_total": round(final_efi, 2),
            "expected_outcome": round(expected_v, 2),
            "cvar_shortfall": round(cvar, 2),
            "confidence_score": round(confidence, 3),
            "components": {
                "avg_revenue": round(np.mean(revenue_scenarios), 2),
                "avg_cost": round(np.mean(cost_scenarios), 2),
                "avg_penalty": round(np.mean(delay_penalty_scenarios), 2),
                "avg_loss": round(np.mean(loss_factor_scenarios), 2)
            }
        }
