from fastapi import APIRouter
from app.financial_system.adaptive_orchestrator import AdaptiveOrchestrator

router = APIRouter(prefix="/financial-intelligence", tags=["Intelligence"])

# Layer 4: AdaptiveOrchestrator — LLM-dispatched MAS replacing the static pipeline.
# run() is a native coroutine — no asyncio.to_thread needed.
engine = AdaptiveOrchestrator()

@router.get("/")
async def get_intelligence(tenant_id: str = "default_tenant"):
    """
    Executes the adaptive intelligence matrix.
    Layer 4: An LLM dispatcher (temperature=0) decides which MAS agents to run
    based on live portfolio signals. All financial numbers are fully deterministic.
    The LLM is involved only in dispatch planning and CFO narrative synthesis.
    """
    response_data = await engine.run(tenant_id=tenant_id)
    return response_data