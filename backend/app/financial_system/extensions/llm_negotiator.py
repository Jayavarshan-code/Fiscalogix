"""
GenerativeNegotiator — LLM-powered supplier SLA negotiation strategy engine.

Uses the LlmGateway's draft_negotiation_strategy() which:
  - Pulls RAG context from historical supplier/carrier performance
  - Embeds extracted contract penalty clauses as leverage data
  - Returns structured AgentResponse with content + suggested_actions
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GenerativeNegotiator:
    """
    Builds data-driven negotiation payloads by combining:
      1. Supplier performance metrics
      2. NLP-extracted contract penalty clauses (from SLAContractExtractor)
      3. LLM-generated strategy via LlmGateway.draft_negotiation_strategy()
    """

    def __init__(self):
        from app.services.llm_gateway import LlmGateway
        self._gateway = LlmGateway()

    async def generate_negotiation_payload(
        self,
        supplier_data: Dict[str, Any],
        contract_clauses: Optional[List[Dict[str, Any]]] = None,
        tenant_id: str = "default_tenant",
    ) -> Dict[str, Any]:
        """
        Generate a structured negotiation strategy for a supplier.

        Args:
            supplier_data:    Supplier metrics (delay_variance, payment_terms, wacc_cost, etc.)
            contract_clauses: Pre-extracted penalty/bottleneck clauses from SLAContractExtractor.
                              If None, extracts from supplier_data["contract_text"] when present.
            tenant_id:        Tenant scope for RAG retrieval and circuit-breaker keying.

        Returns:
            Dict with strategy narrative, suggested actions, leverage points, and metadata.
        """
        supplier_id = supplier_data.get("supplier_id", "UNKNOWN")

        # Resolve contract clauses — extract on-the-fly if raw text is provided
        if contract_clauses is None:
            contract_text = supplier_data.get("contract_text", "")
            if contract_text:
                from app.ml.sla_extractor import SLAContractExtractor
                extraction = SLAContractExtractor.extract(contract_text)
                contract_clauses = extraction.get("bottleneck_clauses", [])
            else:
                contract_clauses = []

        # Build structured penalty summary for the LLM prompt
        penalty_summary = self._summarize_penalties(contract_clauses, supplier_data)

        try:
            agent_response = await self._gateway.draft_negotiation_strategy(
                supplier_id=supplier_id,
                contract_penalties=penalty_summary,
                performance_data=supplier_data,
                tenant_id=tenant_id,
            )

            return {
                "supplier_id":      supplier_id,
                "strategy":         agent_response.content,
                "suggested_actions": agent_response.suggested_actions,
                "leverage_clauses": [
                    c for c in contract_clauses
                    if c.get("bottleneck_severity") in ("CRITICAL", "HIGH")
                ],
                "penalty_summary":  penalty_summary,
                "status":           "success",
                "llm_engine":       "LlmGateway/draft_negotiation_strategy",
            }

        except Exception as e:
            logger.error(f"GenerativeNegotiator: strategy generation failed for {supplier_id} — {e}")
            return {
                "supplier_id":       supplier_id,
                "strategy":          self._fallback_strategy(supplier_data),
                "suggested_actions": [
                    "Review contract penalty clauses manually",
                    "Escalate to procurement team",
                    "Schedule supplier performance review",
                ],
                "leverage_clauses":  [],
                "penalty_summary":   penalty_summary,
                "status":            "fallback",
                "error":             str(e),
            }

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _summarize_penalties(
        clauses: List[Dict[str, Any]],
        supplier_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Merge NLP-extracted clauses with any heuristic penalty data from supplier_data
        into a clean list suitable for the LLM prompt.
        """
        summary = []

        # Add NLP-extracted clauses
        for c in clauses:
            entry = {
                "type":        c.get("clause_type", "unknown"),
                "description": c.get("raw_text", "")[:200],
                "severity":    c.get("bottleneck_severity", "MEDIUM"),
                "reason":      c.get("bottleneck_reason", ""),
            }
            if c.get("value") is not None:
                entry["value"] = c["value"]
                entry["unit"]  = c.get("unit", "")
            summary.append(entry)

        # Add structured heuristic data if no NLP clauses found
        if not summary:
            wacc_cost = supplier_data.get("wacc_carrying_cost_usd")
            delay_var = supplier_data.get("historical_delay_variance_pct")
            if wacc_cost:
                summary.append({
                    "type":        "wacc_carrying_cost",
                    "description": f"WACC carrying cost of delayed payments: ${wacc_cost:,.0f}/year",
                    "severity":    "HIGH",
                })
            if delay_var:
                summary.append({
                    "type":        "delay_variance",
                    "description": f"Historical delay variance: {delay_var}% of shipments delayed",
                    "severity":    "HIGH" if float(delay_var) > 10 else "MEDIUM",
                })

        return summary

    @staticmethod
    def _fallback_strategy(supplier_data: Dict[str, Any]) -> str:
        sid         = supplier_data.get("supplier_id", "this supplier")
        delay_var   = supplier_data.get("historical_delay_variance_pct", "unknown")
        wacc_cost   = supplier_data.get("wacc_carrying_cost_usd", 0)
        curr_terms  = supplier_data.get("current_payment_terms", 30)
        target_terms = supplier_data.get("target_payment_terms", 60)

        return (
            f"Negotiation brief for {sid} (auto-generated fallback):\n\n"
            f"1. LEVERAGE POINTS\n"
            f"   - Delay variance of {delay_var}% creates ${wacc_cost:,.0f} annual WACC carrying cost.\n"
            f"   - Current Net-{curr_terms} terms are below industry benchmark for this tier.\n\n"
            f"2. PROPOSED TERMS\n"
            f"   - Extend payment terms to Net-{target_terms} to align with cash-cycle requirements.\n"
            f"   - Insert OTIF penalty clause (≥95% threshold, 2%/day non-compliance rate).\n\n"
            f"3. WALKAWAY POSITION\n"
            f"   - If supplier cannot meet Net-{target_terms} and OTIF ≥95%, initiate dual-source qualification."
        )
