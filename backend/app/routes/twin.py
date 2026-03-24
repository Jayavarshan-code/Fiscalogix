import asyncio
from fastapi import APIRouter
from app.financial_system.orchestrator import FinancialIntelligenceOrchestrator

router = APIRouter(prefix="/financial-intelligence", tags=["Intelligence"])

engine = FinancialIntelligenceOrchestrator()

@router.get("/")
async def get_intelligence(tenant_id: str = "default_tenant"):
    """
    Executes the entire enterprise intelligence matrix processing massive concurrent inputs efficiently.
    Uses asyncio multi-threading to natively detach the CPU-heavy calculations from the synchronous server runtime! 
    """
    response_data = await asyncio.to_thread(engine.run, tenant_id)
    return response_data