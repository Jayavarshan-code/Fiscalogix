from fastapi import APIRouter, Depends
from app.financial_system.adaptive_orchestrator import AdaptiveOrchestrator
from app.financial_system.auth import get_current_user

router = APIRouter(prefix="/financial-intelligence", tags=["Intelligence"])

# Layer 4: AdaptiveOrchestrator — LLM-dispatched MAS replacing the static pipeline.
engine = AdaptiveOrchestrator()

@router.get("/")
async def get_intelligence(current_user: dict = Depends(get_current_user)):
    """
    Executes the adaptive intelligence matrix.
    tenant_id is read from the authenticated JWT — no query-param spoofing possible.
    """
    tenant_id = current_user.get("tenant_id", "default_tenant")
    response_data = await engine.run(tenant_id=tenant_id)
    return response_data
