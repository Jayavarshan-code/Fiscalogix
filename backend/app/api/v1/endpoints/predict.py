from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.financial_system.delay_model import DelayPredictionModel

router = APIRouter()
delay_model = DelayPredictionModel()

@router.post("/delay")
async def predict_delay(payload: List[Dict[str, Any]]):
    """
    Enterprise Prediction API:
    Input: List of shipment/route JSON objects.
    Output: Probabilistic delay days per shipment.
    """
    try:
        results = delay_model.compute_batch(payload)
        return {
            "status": "success",
            "predictions": [
                {"shipment_id": payload[i].get("shipment_id"), "predicted_delay_days": float(results[i])}
                for i in range(len(payload))
            ],
            "model_version": "v2.1-stochastic"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
