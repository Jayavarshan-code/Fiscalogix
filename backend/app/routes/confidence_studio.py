from fastapi import APIRouter, Query
from typing import Dict, Any

from app.financial_system.orchestrator import FinancialIntelligenceOrchestrator

router = APIRouter(prefix="/confidence-studio", tags=["Trust"])

engine = FinancialIntelligenceOrchestrator()

@router.get("/explain/{shipment_id}")
async def explain_risk(shipment_id: int, tenant_id: str = Query("default_tenant")):
    """
    Confidence Studio Endpoint: Provide explainable AI mechanics.
    Surfaces the exact 'Why' and 'How' for a single transaction's risk profiling,
    translating 'Black Box' models into CFO-auditable statements.
    """
    # Force single processing for demonstration
    # In reality, this might query pre-computed intelligence caching
    payload = engine.run(tenant_id=tenant_id)
    
    revm_data = payload.get("revm", [])
    
    # Isolate specific shipment
    target_row = next((r for r in revm_data if r.get("shipment_id") == shipment_id), None)
    
    if not target_row:
        return {"error": "Shipment not found or inaccessible for this tenant"}
        
    drivers = target_row.get("risk_drivers", [])
    confidence = target_row.get("risk_confidence", 0.0)
    score = target_row.get("risk_score", 0.0)
    
    return {
        "shipment_id": shipment_id,
        "tenant_id": tenant_id,
        "model_confidence": confidence,
        "risk_probability": score,
        "key_drivers": drivers,
        "narrative": f"The system assigned a {(score*100):.1f}% failure risk to this transit with {(confidence*100):.1f}% AI confidence. Primary structural drivers forming this conclusion were: {', '.join(drivers)}."
    }
