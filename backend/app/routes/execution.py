from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.connectors.sap import SAPS4HanaConnector
from app.connectors.netsuite import NetSuiteConnector
from app.financial_system.audit_logger import AuditLogger
from app.financial_system.permission_engine import PermissionEngine
from app.Db.connections import get_db
from app.connectors.netsuite import NetSuiteConnector

router = APIRouter(prefix="/execution", tags=["Execution"])

class ExecutionPayload(BaseModel):
    tenant_id: str
    action_type: str  # e.g. REROUTE, EXPEDITE, CANCEL
    shipment_id: str
    erp_target: str = "SAP" # Default to SAP, could be NetSuite
    confidence_score: float
    parameters: Optional[Dict[str, Any]] = None
    mock_user_id: int = 1 # Temporary: Passed from frontend to test RBAC

@router.post("/action")
async def execute_action(payload: ExecutionPayload, db: Session = Depends(get_db)):
    """
    Bi-Directional Execution Endpoint.
    Gated by Salesforce-style RBAC Permission Engine.
    """
    try:
        # Step 1: RBAC Permission Gate
        can_execute = PermissionEngine.check_permission(db, payload.mock_user_id, "can_execute")
        if not can_execute:
            raise HTTPException(
                status_code=403, 
                detail="PERMISSION_DENIED: Your profile lacks 'can_execute' permissions for this object."
            )
            
        # Step 2: Route to ERP
            connector = SAPS4HanaConnector()
        elif payload.erp_target.upper() == "NETSUITE":
            connector = NetSuiteConnector()
        else:
            raise HTTPException(status_code=400, detail="Invalid ERP target specified.")
            
        erp_payload = {
            "shipment_id": payload.shipment_id,
            "confidence_score": payload.confidence_score,
            "parameters": payload.parameters or {}
        }
        
        # Fire the Bi-Directional write-back request
        result = await connector.execute_action(
            tenant_id=payload.tenant_id,
            action_type=payload.action_type,
            payload=erp_payload
        )
        
        # Phase 2: Immutable Audit Logging (SOC2 Compliance)
        AuditLogger.log_execution(
            db=db,
            tenant_id=payload.tenant_id,
            user_id="UI_OPERATOR", # Hardcoded for now until Auth is added
            action_type=payload.action_type,
            target_entity_id=payload.shipment_id,
            confidence_score=payload.confidence_score,
            erp_receipt=result,
            previous_state={"status": "IN_TRANSIT_DELAYED"}, # Placeholder
            new_state={"status": "REROUTED", "action_applied": payload.action_type}
        )
        
        return {
            "execution_status": "CONFIRMED",
            "message": f"Successfully executed {payload.action_type} on {payload.shipment_id}",
            "erp_receipt": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")
