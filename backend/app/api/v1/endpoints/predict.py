from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.Db.connections import get_db
from app.financial_system.dw_schema import DWShipmentFact
from app.financial_system.delay_model import DelayPredictionModel
from app.financial_system.risk_engine import RiskEngine
from app.financial_system.executive.monte_carlo import MonteCarloEngine

router = APIRouter()
delay_model = DelayPredictionModel()
risk_engine = RiskEngine()
mc_engine = MonteCarloEngine()

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

@router.get("/shipment/{shipment_id}/insights")
async def get_shipment_insights(shipment_id: str, db: Session = Depends(get_db)):
    """
    Live Executive Cockpit API.
    Provides SHAP value drivers and Monte Carlo stochastic arrays for dynamic UI rendering.
    """
    # 1. Fetch Shipment
    if shipment_id.startswith("SYS-"):
        db_id = int(shipment_id.replace("SYS-", ""))
        shipment = db.query(DWShipmentFact).filter(DWShipmentFact.id == db_id).first()
    else:
        shipment = db.query(DWShipmentFact).filter(DWShipmentFact.raw_source_uuid == shipment_id).first()

    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # 2. Extract specific drivers (SHAP)
    row_data = {
        "route": f"{shipment.origin_node or 'UNKNOWN'} -> {shipment.destination_node or 'UNKNOWN'}",
        "order_value": shipment.total_value_usd or 10000,
        "total_cost": (shipment.total_value_usd or 10000) * 0.85,
        "contribution_profit": shipment.margin_usd or 1500,
        "credit_days": 30
    }
    
    predicted_delay = shipment.delay_days_calculated or 2
    risk_output = risk_engine.compute(row_data, predicted_delay)
    
    # Example SHAP drivers (or fallback heuristic drivers) from the risk engine
    drivers_list = risk_output.get("drivers", [])
    executive_narrative = (
        f"Dynamic Risk Output: {drivers_list[0] if drivers_list else 'Standard risk patterns detected.'} "
        f"Probability of failure is {(risk_output.get('score', 0) * 100):.1f}%."
    )

    # 3. Simulate Monte Carlo Scenarios for the Chart
    enriched_record = {
        **row_data,
        "predicted_delay": predicted_delay,
        "risk_score": risk_output.get("score", 0.05),
        "wacc": 0.08,
        "fx_cost": 0.0,
        "revm": (shipment.margin_usd or 1500) - ((shipment.total_value_usd or 10000) * risk_output.get("score", 0.05))
    }
    
    mc_output = mc_engine.simulate_var([enriched_record], iterations=1000)
    scenarios = mc_output.get("scenarios", [])

    return {
        "recommended_action": "Reroute via Alternate Hub" if risk_output.get('score', 0) > 0.5 else "Proceed standard route",
        "profit_impact_delta": (shipment.margin_usd or 1500) * 0.9,
        "risk_reduction_pct": f"{(risk_output.get('score', 0) * 0.8 * 100):.1f}%",
        "confidence_score": risk_output.get("confidence", 0.95),
        "operational_alert": "Critical disruption detected" if risk_output.get('score', 0) > 0.8 else "Nominal operation",
        "executive_narrative": executive_narrative,
        "monte_carlo_scenarios": scenarios,
        "components": {
            "avg_revenue": shipment.total_value_usd or 10000,
            "avg_cost": (shipment.total_value_usd or 10000) - (shipment.margin_usd or 1500),
            "avg_penalty": (shipment.total_value_usd or 10000) * 0.02 * predicted_delay,
            "avg_loss": 5000
        },
        "granular_breakdown": {
            "costs": { "transport": 6000, "handling": 1000 },
            "losses": { "damage": 500, "spoilage": 0 }
        }
    }

from app.financial_system.executive.cashflow import PredictiveCashflowEngine

@router.get("/cashflow/trajectory")
async def get_cashflow_trajectory(tenant_id: str = "default_tenant", db: Session = Depends(get_db)):
    """
    Enterprise API overriding static timelines with AR-driven ML models.
    Returns probabilistic cashflow expectations.
    """
    try:
        payload = PredictiveCashflowEngine.simulate_trajectory(db, tenant_id)
        return payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
