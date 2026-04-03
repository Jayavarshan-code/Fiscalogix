from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.connectors.sap import SAPS4HanaConnector
from app.connectors.netsuite import NetSuiteConnector
from app.financial_system.audit_logger import AuditLogger
from app.financial_system.permission_engine import PermissionEngine
from app.financial_system.dependencies import get_current_user
from app.Db.connections import get_db

router = APIRouter(prefix="/execution", tags=["Execution"])

class ExecutionPayload(BaseModel):
    action_type: str  # e.g. REROUTE, EXPEDITE, CANCEL
    shipment_id: str
    erp_target: str = "SAP"
    confidence_score: float
    parameters: Optional[Dict[str, Any]] = None

@router.post("/action")
async def execute_action(
    payload: ExecutionPayload,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)  # 🔐 JWT-Protected
):
    """
    Bi-Directional Execution Endpoint.
    JWT-Gated + Salesforce-style RBAC Permission Engine.
    tenant_id pulled directly from the verified JWT token.
    """
    try:
        user_id = current_user.get("user_id")
        tenant_id = current_user.get("tenant_id", "default_tenant")

        # Step 1: RBAC Permission Gate (using the REAL user_id from the JWT)
        can_execute = PermissionEngine.check_permission(db, user_id, "can_execute")
        if not can_execute:
            raise HTTPException(
                status_code=403,
                detail="PERMISSION_DENIED: Your profile lacks 'can_execute' permissions for this object."
            )

        # Step 2: Route to correct ERP (FIXED: was broken if/elif)
        if payload.erp_target.upper() == "SAP":
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
            tenant_id=tenant_id,
            action_type=payload.action_type,
            payload=erp_payload
        )

        # Phase 2: Immutable Audit Logging (SOC2 Compliance)
        AuditLogger.log_execution(
            db=db,
            tenant_id=tenant_id,
            user_id=str(user_id),
            action_type=payload.action_type,
            target_entity_id=payload.shipment_id,
            confidence_score=payload.confidence_score,
            erp_receipt=result,
            previous_state={"status": "IN_TRANSIT_DELAYED"},
            new_state={"status": "REROUTED", "action_applied": payload.action_type}
        )

        return {
            "execution_status": "CONFIRMED",
            "message": f"Successfully executed {payload.action_type} on {payload.shipment_id}",
            "erp_receipt": result
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")
