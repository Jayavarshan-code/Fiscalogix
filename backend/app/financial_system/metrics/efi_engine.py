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
        breakdown: Dict[str, Any] = None,
        risk_aversion_lambda: float = 1.0,
        alpha: float = 0.1,
        discount_rate: float = 0.0,
        time_t: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculates the hardened EFI score based on N simulated scenarios.
        """
        # --- Vectorized Matrix Arithmetic ---
        rev = np.array(revenue_scenarios)
        cost = np.array(cost_scenarios)
        pen = np.array(delay_penalty_scenarios)
        loss = np.array(loss_factor_scenarios)
        
        num_scenarios = len(rev)
        if num_scenarios == 0: return {"efi_total": 0, "confidence": 0}

        # Compute V_i for all scenarios simultaneously
        outcomes = rev - cost - pen - loss
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

        # 4. Confidence Score (1 - (σ / |EFI|))
        std_dev = float(np.std(outcomes))
        abs_efi = abs(final_efi)
        confidence = 1 - (std_dev / abs_efi) if abs_efi > 0 else 0.5
        confidence = max(0.1, min(0.99, confidence))

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
