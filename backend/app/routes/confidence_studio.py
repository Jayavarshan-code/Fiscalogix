from fastapi import APIRouter, Query
from typing import Dict, Any

from app.financial_system.adaptive_orchestrator import AdaptiveOrchestrator

router = APIRouter(prefix="/confidence-studio", tags=["Trust"])

engine = AdaptiveOrchestrator()

@router.get("/explain/{shipment_id}")
async def explain_risk(shipment_id: int, tenant_id: str = Query("default_tenant")):
    """
    Confidence Studio: Explainable AI mechanics for a single shipment.
    Surfaces the 'Why' and 'How' behind each risk score using Layer 4 MAS outputs.
    The executive brief from the AdaptiveOrchestrator is included for full context.
    """
    payload = await engine.run(tenant_id=tenant_id)

    revm_data = payload.get("revm", [])

    # Isolate specific shipment
    target_row = next((r for r in revm_data if r.get("shipment_id") == shipment_id), None)

    if not target_row:
        return {"error": "Shipment not found or inaccessible for this tenant"}

    drivers = target_row.get("risk_drivers", [])
    confidence = target_row.get("risk_confidence", 0.0)
    score = target_row.get("risk_score", 0.0)
    intelligence = payload.get("intelligence", {})

    return {
        "shipment_id": shipment_id,
        "tenant_id": tenant_id,
        "model_confidence": confidence,
        "risk_probability": score,
        "key_drivers": drivers,
        "narrative": (
            f"The system assigned a {(score*100):.1f}% failure risk to this transit "
            f"with {(confidence*100):.1f}% AI confidence. "
            f"Primary structural drivers: {', '.join(drivers) if drivers else 'N/A'}."
        ),
        # New: include MAS intelligence layer outputs
        "cfo_brief":     intelligence.get("cfo_brief", ""),
        "dispatch_plan": intelligence.get("dispatch_plan", []),
        "situation":     intelligence.get("situation", {}),
    }
