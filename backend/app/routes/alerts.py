"""
Alerts Router

GET  /alerts/thresholds          — current thresholds for the tenant
POST /alerts/configure           — update thresholds
POST /alerts/check               — manually trigger alert evaluation
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.financial_system.auth import get_current_user
from app.services.alert_service import get_thresholds, set_thresholds, AlertService

router = APIRouter(prefix="/alerts", tags=["Alerts & Notifications"])


class ThresholdConfig(BaseModel):
    cash_deficit_usd:    Optional[float] = None
    high_risk_shipments: Optional[int]   = None
    confidence_floor:    Optional[float] = None
    alert_email:         Optional[str]   = None   # overrides ALERT_EMAIL env var for this tenant
    alert_whatsapp_to:   Optional[str]   = None   # e.g. "whatsapp:+919876543210"


@router.get("/thresholds")
def get_alert_thresholds(current_user: dict = Depends(get_current_user)):
    tenant_id = current_user.get("tenant_id", "default_tenant")
    return {"tenant_id": tenant_id, "thresholds": get_thresholds(tenant_id)}


@router.post("/configure")
def configure_alerts(
    config: ThresholdConfig,
    current_user: dict = Depends(get_current_user),
):
    tenant_id = current_user.get("tenant_id", "default_tenant")
    updates = {k: v for k, v in config.model_dump().items() if v is not None and k != "alert_email"}
    set_thresholds(tenant_id, updates)

    import os
    if config.alert_email:
        os.environ["ALERT_EMAIL"] = config.alert_email
    if config.alert_whatsapp_to:
        os.environ["ALERT_WHATSAPP_TO"] = config.alert_whatsapp_to

    return {"message": "Alert thresholds updated.", "thresholds": get_thresholds(tenant_id)}


@router.post("/check")
async def manual_alert_check(current_user: dict = Depends(get_current_user)):
    """
    Manually triggers an alert evaluation against live financial data.
    Used by the frontend to check for alerts on demand.
    """
    from app.financial_system.adaptive_orchestrator import AdaptiveOrchestrator
    tenant_id = current_user.get("tenant_id", "default_tenant")

    orchestrator = AdaptiveOrchestrator()
    financial_data = await orchestrator.run(tenant_id=tenant_id)
    thresholds = get_thresholds(tenant_id)
    alerts = AlertService.check(financial_data, tenant_id, thresholds)

    return {
        "tenant_id": tenant_id,
        "alerts_fired": len(alerts),
        "alerts": alerts,
    }
