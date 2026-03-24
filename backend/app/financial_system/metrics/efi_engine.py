from typing import Dict, List, Any
import numpy as np

class UniversalEFIEngine:
    """
    Pillar Alignment: The "Soul" of decision intelligence.
    Standardizes EFI (Expected Financial Impact) calculation across all business objects.
    """
    
    @staticmethod
    def calculate_efi(base_margin: float, risk_drivers: Dict[str, float], black_swan_reserve: float = 0.0) -> Dict[str, Any]:
        """
        Calculates EFI based on a baseline margin and a set of probabilistic drivers.
        
        EFI = Base Margin - Sum(Risk Penalties) - Black Swan (CVaR) Reserve
        """
        total_risk_penalty = sum(risk_drivers.values())
        final_efi = base_margin - total_risk_penalty - black_swan_reserve
        
        return {
            "efi_total": round(final_efi, 2),
            "efi_breakdown": {
                "base_margin": round(base_margin, 2),
                "risk_penalties": {k: round(v, 2) for k, v in risk_drivers.items()},
                "tail_risk_reserve": round(black_swan_reserve, 2)
            },
            "resilience_index": round((final_efi / base_margin * 100) if base_margin > 0 else 0, 1)
        }

    @staticmethod
    def dollarize_narrative(efi_data: Dict[str, Any]) -> str:
        """Translates EFI data into human-readable executive insights."""
        total = efi_data["efi_total"]
        reserve = efi_data["efi_breakdown"]["tail_risk_reserve"]
        
        if reserve > (total * 0.2):
            return f"EFI of ₹{total:,} includes a significant reserve for high-volatility scenarios."
        return f"Standard EFI outlook of ₹{total:,} based on expected market conditions."
