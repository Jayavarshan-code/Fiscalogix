from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.financial_system.optimization.stochastic_mip_optimizer import StochasticMIPOptimizer

router = APIRouter()
optimizer = StochasticMIPOptimizer()

@router.post("/efi")
async def optimize_efi(
    candidate_matrix: List[List[Dict[str, Any]]], 
    available_cash: float = 1000000.0,
    risk_appetite: str = "BALANCED"
):
    """
    Enterprise Optimization API:
    Input: candidate_matrix (Shipments -> Actions), cash limit, risk appetite.
    Output: EFI-optimized decision set with executive narratives.
    """
    try:
        decisions = optimizer.optimize(candidate_matrix, available_cash, risk_appetite)
        return {
            "status": "success",
            "optimized_decisions": decisions,
            "metadata": {
                "algorithm": "StochasticMIP",
                "risk_posture": risk_appetite,
                "performance_mode": "Vectorized"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
