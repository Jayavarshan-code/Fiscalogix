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
        duty_scenarios: List[float] = None, # New: Export/Import Duties
        tariff_risk_scenarios: List[float] = None, # New: Tariff volatility
        hidden_fee_scenarios: List[float] = None, # New: Demurrage/Detention/Surcharges
        holding_cost_scenarios: List[float] = None,
        opportunity_cost_scenarios: List[float] = None,
        breakdown: Dict[str, Any] = None,
        risk_aversion_lambda: float = 1.0,
        alpha: float = 0.1,
        discount_rate: float = 0.0,
        time_t: float = 0.0,
        fidelity_score: float = 1.0
    ) -> Dict[str, Any]:
        """
        Calculates the hardened EFI score including Total Landed Cost (TLC) factors.
        """
        rev = np.array(revenue_scenarios)
        cost = np.array(cost_scenarios)
        pen = np.array(delay_penalty_scenarios)
        loss = np.array(loss_factor_scenarios)
        
        # New: Duty and Tax factors
        duty = np.array(duty_scenarios) if duty_scenarios is not None else np.zeros_like(rev)
        tariff = np.array(tariff_risk_scenarios) if tariff_risk_scenarios is not None else np.zeros_like(rev)
        hidden = np.array(hidden_fee_scenarios) if hidden_fee_scenarios is not None else np.zeros_like(rev)
        
        hold = np.array(holding_cost_scenarios) if holding_cost_scenarios is not None else np.zeros_like(rev)
        opp = np.array(opportunity_cost_scenarios) if opportunity_cost_scenarios is not None else np.zeros_like(rev)
        
        num_scenarios = len(rev)
        if num_scenarios == 0: return {"efi_total": 0, "confidence": 0}

        # Comprehensive Formula: V = R - (C + P + L + D + T + H + H_old + O)
        outcomes = rev - (cost + pen + loss + duty + tariff + hidden + hold + opp)
        
        if discount_rate > 0 and time_t > 0:
            outcomes = outcomes / ((1 + discount_rate) ** time_t)

        # 2. Risk Adjustment (CVaR)
        n_worst = max(1, int(num_scenarios * alpha))
        sorted_outcomes = np.sort(outcomes)
        worst_cases = sorted_outcomes[:n_worst]
        cvar = float(np.mean(worst_cases))
        
        # 3. Final EFI Score (Expectation - Lambda * |CVaR|)
        expected_v = float(np.mean(outcomes))
        final_efi = expected_v - (risk_aversion_lambda * abs(min(0, cvar)))

        # 4. Confidence Score & Data Fidelity
        std_dev = float(np.std(outcomes))
        abs_efi = abs(final_efi)
        raw_confidence = 1 - (std_dev / abs_efi) if abs_efi > 0 else 0.5
        fidelity_penalty = (1.0 - fidelity_score) * 0.5
        confidence = max(0.01, min(0.99, raw_confidence - fidelity_penalty))

        # 5. Summarize Granular Breakdown
        avg_breakdown = {}
        if breakdown:
            for category, sub_components in breakdown.items():
                avg_breakdown[category] = {
                    k: round(float(np.mean(v)), 2) for k, v in sub_components.items()
                }

        return {
            "efi_headline": round(final_efi, 2),
            "breakdown": {
                "delay_cost": round(float(np.mean(cost + duty + tariff)), 2), # Capital decay in transit
                "penalty_cost": round(float(np.mean(pen + hidden)), 2),     # Contractual/Physical Fines
                "inventory_holding": round(float(np.mean(hold)), 2),         # Stock on hand burn
                "opportunity_cost": round(float(np.mean(opp)), 2)            # Stockout/Lost Sales
            },
            "expected_outcome": round(expected_v, 2),
            "confidence_score": round(confidence, 3),
            "data_fidelity": round(fidelity_score, 2)
        }
