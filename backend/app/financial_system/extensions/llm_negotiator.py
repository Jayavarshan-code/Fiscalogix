from app.services.llm_gateway import LlmGateway

class GenerativeNegotiator:
    """
    Constructs and executes highly tactical, data-driven LLM strategies
    to aggressively negotiate supplier SLA terms.
    """
    def __init__(self):
        self.llm_gateway = LlmGateway()

    async def generate_negotiation_payload(self, supplier_data: dict):
        supplier_id = supplier_data.get("supplier_id", "UNKNOWN")
        delay_variance = supplier_data.get("historical_delay_variance_pct", 15.0)
        current_terms = supplier_data.get("current_payment_terms", 30)
        target_terms = supplier_data.get("target_payment_terms", 60)
        wacc_cost_usd = supplier_data.get("wacc_carrying_cost_usd", 12500.0)

        # 1. Create the reasoning prompts
        system_prompt = (
            "You are an aggressive, data-driven Chief Procurement Officer. "
            "Negotiate better payment terms based on supplier underperformance."
        )
        user_prompt = f"Negotiation for {supplier_id}. Delay: {delay_variance}%. WACC Cost: ${wacc_cost_usd}."
        
        # 2. Execute via the Unified Brain
        agent_response = await self.llm_gateway.draft_negotiation_strategy(
            supplier_id=supplier_id,
            contract_penalties=[], # To be filled by Pillar 9 sync
            performance_data=supplier_data
        )
        
        return {
            "supplier_id": supplier_id,
            "llm_engine": "AGENTIC_GATEWAY",
            "strategy": agent_response.content,
            "actions": agent_response.suggested_actions,
            "status": "EXECUTED_BY_BRAIN"
        }
