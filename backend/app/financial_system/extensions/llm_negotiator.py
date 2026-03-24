class GenerativeNegotiator:
    """
    Constructs highly tactical, data-driven LLM prompt payloads simulating LLaMA/Grok execution 
    to aggressively negotiate supplier SLA terms.
    """
    def generate_negotiation_payload(self, supplier_data):
        supplier_id = supplier_data.get("supplier_id", "UNKNOWN")
        delay_variance = supplier_data.get("historical_delay_variance_pct", 15.0) # e.g. 15.0 for 15% worse than market
        current_terms = supplier_data.get("current_payment_terms", 30)
        target_terms = supplier_data.get("target_payment_terms", 60)
        wacc_cost_usd = supplier_data.get("wacc_carrying_cost_usd", 12500.0)

        # Strict execution context bridging the ML data directly to Natural Language
        system_prompt = (
            "You are an aggressive, data-driven Chief Procurement Officer for a globally dominant logistics firm. "
            "Your objective is to negotiate better payment terms from suppliers who are structurally underperforming "
            "and penalizing our Working Capital. Respond only with the exact drafted email. Maintain fierce professionalism."
        )

        user_prompt = f"""
We need to renegotiate our contract with Supplier {supplier_id}.
Here is the strict telemetry data from our Intelligence Engine:
- They are delivering {delay_variance}% slower than the algorithmic industry average.
- Their delays are actively costing us explicitly ${wacc_cost_usd} in WACC capital lockup.
- Our current payment terms are Net-{current_terms}.

Draft a firm, professional email to their corporate operations team. Demand that we functionally adjust our payment terms to Net-{target_terms} to mathematically offset our capital costs given their delay variance. Inform them that if they do not comply, our Profit Optimization Engine will algorithmically route our future order volume to a different tier-1 vendor.
        """
        
        return {
            "supplier_id": supplier_id,
            "llm_engine": "LLAMA_OR_GROK",
            "system_prompt": system_prompt,
            "user_prompt": user_prompt.strip(),
            "status": "READY_FOR_LLM_EXECUTION"
        }
