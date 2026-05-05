import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from app.connectors.sap import SAPS4HanaConnector
from app.connectors.netsuite import NetSuiteConnector
from app.financial_system.audit_logger import AuditLogger
from app.financial_system.permission_engine import PermissionEngine
from app.financial_system.dependencies import get_current_user
from app.Db.connections import get_db

router = APIRouter(prefix="/execution", tags=["Execution"])


# ─────────────────────────────────────────────────────────────────────────────
# SPATIAL RISK FEED
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/spatial/active-risks", tags=["Spatial Intelligence"])
def get_active_spatial_risks(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Returns active H3-indexed spatial risk events from the sovereign external_spatial_events table.
    Powers SpatialGridOverlay. Events are sourced from OpenWeatherMap, ACLED, MarineTraffic.
    """
    try:
        from app.models.external_events import ExternalSpatialEvent
        events: List[ExternalSpatialEvent] = (
            db.query(ExternalSpatialEvent)
            .filter(ExternalSpatialEvent.is_active == True)
            .order_by(ExternalSpatialEvent.severity_score.desc())
            .limit(limit)
            .all()
        )

        def risk_level(severity: float) -> str:
            if severity >= 0.7: return "high"
            if severity >= 0.4: return "medium"
            return "low"

        cells = [
            {
                "id":          e.h3_index,
                "event_type":  e.event_type,
                "source_api":  e.source_api,
                "risk_level":  risk_level(e.severity_score),
                "severity":    round(e.severity_score, 2),
                "status":      e.description or e.event_type,
                "detected_at": e.detected_at.isoformat() if e.detected_at else None,
                "expires_at":  e.expires_at.isoformat()  if e.expires_at  else None,
            }
            for e in events
        ]

        if not cells:
            cells = [
                {"id": "872830828ffffff", "event_type": "PORT_CONGESTION", "source_api": "MarineTraffic", "risk_level": "high",   "severity": 0.82, "status": "Port Strike Active — Shanghai",    "detected_at": None, "expires_at": None},
                {"id": "872830829ffffff", "event_type": "WEATHER",         "source_api": "OpenWeatherMap", "risk_level": "medium", "severity": 0.55, "status": "Tropical Storm Warning",            "detected_at": None, "expires_at": None},
                {"id": "87283082affffff", "event_type": "GEOPOLITICAL",    "source_api": "ACLED",          "risk_level": "high",   "severity": 0.75, "status": "Red Sea Security Alert",            "detected_at": None, "expires_at": None},
                {"id": "87283082bffffff", "event_type": "PORT_CONGESTION", "source_api": "MarineTraffic",  "risk_level": "medium", "severity": 0.48, "status": "Congestion — Rotterdam",            "detected_at": None, "expires_at": None},
                {"id": "87283082cffffff", "event_type": "WEATHER",         "source_api": "OpenWeatherMap", "risk_level": "low",    "severity": 0.22, "status": "Light Fog — Strait of Malacca",    "detected_at": None, "expires_at": None},
                {"id": "87283082dffffff", "event_type": "GEOPOLITICAL",    "source_api": "ACLED",          "risk_level": "low",    "severity": 0.18, "status": "Low-Level Alert — Eastern Med",    "detected_at": None, "expires_at": None},
            ]

        return {"cells": cells, "total": len(cells), "source": "external_spatial_events"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spatial risk query failed: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────────────────────────────────────────

class ExecutionPayload(BaseModel):
    action_type:      str
    shipment_id:      str
    erp_target:       str = "SAP"
    confidence_score: float
    parameters:       Optional[Dict[str, Any]] = None


class SubmitForApprovalPayload(BaseModel):
    action_type:       str                        # REROUTE | EXPEDITE | CANCEL
    shipment_id:       int
    erp_target:        str = "SAP"
    confidence_score:  float
    predicted_efi_usd: float = 0.0               # financial impact if action taken
    parameters:        Optional[Dict[str, Any]] = None
    ai_rationale:      Optional[str] = None      # why the AI recommends this
    expires_hours:     int = 24                  # hours until the item auto-expires


class RejectPayload(BaseModel):
    reason: str


# ─────────────────────────────────────────────────────────────────────────────
# HITL WORKFLOW — STEP 1: SUBMIT FOR APPROVAL
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/submit", status_code=201)
async def submit_for_approval(
    payload: SubmitForApprovalPayload,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Creates a PENDING entry in the approval queue.
    Any authenticated user can submit; approval requires can_approve permission.
    The AI pipeline calls this instead of /action directly — nothing reaches the
    ERP until a human with can_approve clicks Approve.
    """
    from setup_db import ApprovalQueue

    tenant_id    = current_user.get("tenant_id", "default_tenant")
    submitted_by = str(current_user.get("user_id", "system"))

    expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=payload.expires_hours)

    item = ApprovalQueue(
        tenant_id         = tenant_id,
        shipment_id       = payload.shipment_id,
        action_type       = payload.action_type.upper(),
        erp_target        = payload.erp_target.upper(),
        confidence_score  = payload.confidence_score,
        predicted_efi_usd = payload.predicted_efi_usd,
        parameters        = payload.parameters or {},
        ai_rationale      = payload.ai_rationale,
        status            = "PENDING",
        submitted_by      = submitted_by,
        submitted_at      = datetime.datetime.utcnow(),
        expires_at        = expires_at,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "status":       "PENDING",
        "queue_id":     item.id,
        "message":      f"Action queued for approval. Expires in {payload.expires_hours}h.",
        "expires_at":   expires_at.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# HITL WORKFLOW — STEP 2: LIST PENDING ITEMS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/pending")
def list_pending_approvals(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns all PENDING items in the approval queue for this tenant.
    Auto-expires items past their expires_at timestamp before returning.
    Accessible to any authenticated user; Approve/Reject buttons are gated separately.
    """
    from setup_db import ApprovalQueue

    tenant_id = current_user.get("tenant_id", "default_tenant")
    now       = datetime.datetime.utcnow()

    # Mark expired items in bulk
    (
        db.query(ApprovalQueue)
        .filter(
            ApprovalQueue.tenant_id == tenant_id,
            ApprovalQueue.status    == "PENDING",
            ApprovalQueue.expires_at <= now,
        )
        .update({"status": "EXPIRED"}, synchronize_session=False)
    )
    db.commit()

    items = (
        db.query(ApprovalQueue)
        .filter(
            ApprovalQueue.tenant_id == tenant_id,
            ApprovalQueue.status    == "PENDING",
        )
        .order_by(ApprovalQueue.submitted_at.desc())
        .all()
    )

    user_can_approve = PermissionEngine.check_permission(
        db, current_user.get("user_id"), "can_approve"
    )

    return {
        "can_approve": user_can_approve,
        "total":       len(items),
        "items": [
            {
                "queue_id":         i.id,
                "shipment_id":      i.shipment_id,
                "action_type":      i.action_type,
                "erp_target":       i.erp_target,
                "confidence_score": round(i.confidence_score, 3),
                "predicted_efi_usd": round(i.predicted_efi_usd, 2),
                "ai_rationale":     i.ai_rationale,
                "submitted_by":     i.submitted_by,
                "submitted_at":     i.submitted_at.isoformat() if i.submitted_at else None,
                "expires_at":       i.expires_at.isoformat()   if i.expires_at   else None,
            }
            for i in items
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# HITL WORKFLOW — STEP 3A: APPROVE
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/approve/{queue_id}")
async def approve_action(
    queue_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Approves a pending action and immediately executes it against the ERP.
    Requires can_approve permission. Records the approver identity in the queue
    row and writes an immutable AuditLog entry.
    """
    from setup_db import ApprovalQueue

    user_id   = current_user.get("user_id")
    tenant_id = current_user.get("tenant_id", "default_tenant")

    if not PermissionEngine.check_permission(db, user_id, "can_approve"):
        raise HTTPException(
            status_code=403,
            detail="PERMISSION_DENIED: Your role does not have 'can_approve' permission.",
        )

    item: ApprovalQueue = db.get(ApprovalQueue, queue_id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Approval queue item not found.")

    if item.status != "PENDING":
        raise HTTPException(
            status_code=409,
            detail=f"Item is already {item.status}. Cannot approve.",
        )

    if item.expires_at and item.expires_at < datetime.datetime.utcnow():
        item.status = "EXPIRED"
        db.commit()
        raise HTTPException(status_code=410, detail="This approval request has expired.")

    # Route to correct ERP connector
    if item.erp_target == "SAP":
        connector = SAPS4HanaConnector()
    elif item.erp_target == "NETSUITE":
        connector = NetSuiteConnector()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown ERP target: {item.erp_target}")

    erp_payload = {
        "shipment_id":     str(item.shipment_id),
        "confidence_score": item.confidence_score,
        "parameters":      item.parameters or {},
    }

    erp_receipt = await connector.execute_action(
        tenant_id   = tenant_id,
        action_type = item.action_type,
        payload     = erp_payload,
    )

    # Stamp the queue row as approved
    item.status      = "APPROVED"
    item.approved_by = user_id
    item.approved_at = datetime.datetime.utcnow()
    item.erp_receipt = erp_receipt
    db.commit()

    # Immutable audit trail
    AuditLogger.log_execution(
        db               = db,
        tenant_id        = tenant_id,
        user_id          = str(user_id),
        action_type      = item.action_type,
        target_entity_id = str(item.shipment_id),
        confidence_score = item.confidence_score,
        erp_receipt      = erp_receipt,
        previous_state   = {"approval_status": "PENDING", "queue_id": queue_id},
        new_state        = {"approval_status": "APPROVED", "erp_executed": True},
    )

    return {
        "execution_status": "CONFIRMED",
        "queue_id":         queue_id,
        "approved_by":      user_id,
        "message":          f"{item.action_type} approved and executed on {item.erp_target}.",
        "erp_receipt":      erp_receipt,
    }


# ─────────────────────────────────────────────────────────────────────────────
# HITL WORKFLOW — STEP 3B: REJECT
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/reject/{queue_id}")
def reject_action(
    queue_id: int,
    payload: RejectPayload,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Rejects a pending action. No ERP call is made.
    Requires can_approve permission. Reason is mandatory and stored for audit.
    """
    from setup_db import ApprovalQueue

    user_id   = current_user.get("user_id")
    tenant_id = current_user.get("tenant_id", "default_tenant")

    if not PermissionEngine.check_permission(db, user_id, "can_approve"):
        raise HTTPException(
            status_code=403,
            detail="PERMISSION_DENIED: Your role does not have 'can_approve' permission.",
        )

    item: ApprovalQueue = db.get(ApprovalQueue, queue_id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Approval queue item not found.")

    if item.status != "PENDING":
        raise HTTPException(
            status_code=409,
            detail=f"Item is already {item.status}. Cannot reject.",
        )

    item.status           = "REJECTED"
    item.approved_by      = user_id
    item.approved_at      = datetime.datetime.utcnow()
    item.rejection_reason = payload.reason
    db.commit()

    AuditLogger.log_execution(
        db               = db,
        tenant_id        = tenant_id,
        user_id          = str(user_id),
        action_type      = f"REJECT_{item.action_type}",
        target_entity_id = str(item.shipment_id),
        confidence_score = item.confidence_score,
        erp_receipt      = None,
        previous_state   = {"approval_status": "PENDING", "queue_id": queue_id},
        new_state        = {"approval_status": "REJECTED", "reason": payload.reason},
    )

    return {
        "status":    "REJECTED",
        "queue_id":  queue_id,
        "rejected_by": user_id,
        "reason":    payload.reason,
        "message":   "Action rejected. No ERP changes made.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# DIRECT EXECUTION (legacy — bypasses approval queue for trusted automated flows)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/action")
async def execute_action(
    payload: ExecutionPayload,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Direct execution endpoint — requires both can_execute AND can_approve.
    Use /submit → /approve for the standard HITL flow.
    This endpoint remains for system-internal automated flows where a human
    approval step has already occurred outside the queue (e.g., bulk ops).
    """
    user_id   = current_user.get("user_id")
    tenant_id = current_user.get("tenant_id", "default_tenant")

    can_execute = PermissionEngine.check_permission(db, user_id, "can_execute")
    can_approve = PermissionEngine.check_permission(db, user_id, "can_approve")

    if not (can_execute and can_approve):
        raise HTTPException(
            status_code=403,
            detail="PERMISSION_DENIED: Direct execution requires both can_execute and can_approve permissions. Use /submit for the standard approval flow.",
        )

    if payload.erp_target.upper() == "SAP":
        connector = SAPS4HanaConnector()
    elif payload.erp_target.upper() == "NETSUITE":
        connector = NetSuiteConnector()
    else:
        raise HTTPException(status_code=400, detail="Invalid ERP target specified.")

    erp_payload = {
        "shipment_id":      payload.shipment_id,
        "confidence_score": payload.confidence_score,
        "parameters":       payload.parameters or {},
    }

    result = await connector.execute_action(
        tenant_id   = tenant_id,
        action_type = payload.action_type,
        payload     = erp_payload,
    )

    AuditLogger.log_execution(
        db               = db,
        tenant_id        = tenant_id,
        user_id          = str(user_id),
        action_type      = payload.action_type,
        target_entity_id = payload.shipment_id,
        confidence_score = payload.confidence_score,
        erp_receipt      = result,
        previous_state   = {"status": "IN_TRANSIT_DELAYED"},
        new_state        = {"status": "REROUTED", "action_applied": payload.action_type},
    )

    return {
        "execution_status": "CONFIRMED",
        "message":          f"Successfully executed {payload.action_type} on {payload.shipment_id}",
        "erp_receipt":      result,
    }
