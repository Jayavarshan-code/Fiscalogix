"""
LLM Gateway — Layer 1 of the Fiscalogix Intelligence Stack.

Design principles:
- Single entry point for ALL LLM calls in the codebase. No other file imports anthropic directly.
- execute() is the only raw call. Every domain method builds on it.
- temperature=0.0 for dispatch/classification decisions (deterministic).
- temperature=0.3 for narrative synthesis (allow prose variation, numbers locked in prompt).
- Graceful degradation: if ANTHROPIC_API_KEY is missing, every call returns a structured
  fallback string so the financial math layer continues to function without the LLM.
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List

import anthropic
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_MODEL = "claude-opus-4-5"          # pinned — change via env var LLM_MODEL
_MAX_TOKENS = 2048


def _get_rag_context(query: str, tenant_id: str, source_types=None) -> str:
    """
    Safely retrieves RAG context — returns empty string on any failure.
    Defensive wrapper so LLM calls never fail due to RAG errors.
    """
    try:
        from app.services.rag import get_retriever
        return get_retriever().get_context(query, tenant_id, source_types=source_types)
    except Exception as e:
        logger.debug(f"RAG context retrieval skipped: {e}")
        return ""


class AgentResponse(BaseModel):
    agent_name: str
    content: str
    suggested_actions: List[str] = []
    metadata: Dict[str, Any] = {}


class LlmGateway:
    """
    Central LLM interface for Fiscalogix.
    All intelligence methods call self.execute() — nowhere else imports anthropic.
    """

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._model = os.environ.get("LLM_MODEL", _MODEL)

        if self._api_key:
            self._client = anthropic.Anthropic(api_key=self._api_key)
            logger.info(f"LlmGateway: initialized with model={self._model}")
        else:
            self._client = None
            logger.warning(
                "LlmGateway: ANTHROPIC_API_KEY not set. "
                "All LLM calls will return degraded fallback responses."
            )

    # ─────────────────────────────────────────────────────────────────────────
    # CORE PRIMITIVES
    # ─────────────────────────────────────────────────────────────────────────

    async def execute(
        self,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int = _MAX_TOKENS,
    ) -> str:
        """
        The single raw LLM call. All domain methods build on this.

        temperature=0.0  → deterministic (dispatch, classification, extraction)
        temperature=0.3  → slight variation allowed (narrative prose)
        """
        if not self._client:
            return self._fallback(user)

        try:
            # anthropic SDK is sync; run in executor to keep FastAPI async-safe
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.messages.create(
                    model=self._model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    # temperature is not a named param in all SDK versions —
                    # pass via extra_body for compatibility
                    **({"temperature": temperature} if temperature != 0.0 else {}),
                ),
            )
            return response.content[0].text

        except anthropic.AuthenticationError:
            logger.error("LlmGateway: Authentication failed — check ANTHROPIC_API_KEY.")
            return self._fallback(user)
        except anthropic.RateLimitError:
            logger.warning("LlmGateway: Rate limit hit — returning fallback.")
            return self._fallback(user)
        except anthropic.APIError as e:
            logger.error(f"LlmGateway: API error — {type(e).__name__}: {e}")
            return self._fallback(user)

    # Convenience sync wrapper for non-async callers (e.g. Celery tasks)
    def execute_sync(self, system: str, user: str, temperature: float = 0.0) -> str:
        if not self._client:
            return self._fallback(user)
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=_MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
                **({"temperature": temperature} if temperature != 0.0 else {}),
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"LlmGateway.execute_sync: {type(e).__name__}: {e}")
            return self._fallback(user)

    def _fallback(self, _user_prompt: str) -> str:
        """
        Returned when the API is unavailable.
        Structured so callers that parse JSON don't crash — they get an
        explicit signal that the LLM is offline rather than a silent empty string.
        """
        logger.warning("LlmGateway: returning degraded fallback response.")
        return (
            "[LLM_OFFLINE] Intelligence layer unavailable. "
            "Deterministic financial calculations remain accurate. "
            "Reconnect ANTHROPIC_API_KEY to enable narrative synthesis and adaptive dispatch."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # DOMAIN METHODS — each maps to a specific intelligence task
    # ─────────────────────────────────────────────────────────────────────────

    async def summarize_risk_panorama(
        self,
        total_revm: float,
        var_95: float,
        risk_events: List[str],
        tenant_id: str = "default_tenant",
    ) -> str:
        """
        Executive risk summary for the CFO dashboard.
        Numbers are injected as ground truth — LLM writes prose only.
        RAG context grounds the response in tenant's historical performance.
        """
        rag_context = _get_rag_context(
            query="portfolio risk disruption route performance",
            tenant_id=tenant_id,
            source_types=["carrier_performance", "route_performance", "shipment_history"],
        )
        system = (
            "You are a CFO advisor at a global logistics intelligence firm. "
            "Write a 3-sentence executive risk summary. "
            "Use only the figures provided. Never invent numbers. "
            "Tone: direct, no hedging, board-room ready."
        )
        user = (
            f"Portfolio ReVM: ${total_revm:,.0f}\n"
            f"Value at Risk (95%): ${var_95:,.0f}\n"
            f"Active disruptions: {', '.join(risk_events) if risk_events else 'None'}\n"
            + (f"\nHistorical context:\n{rag_context}\n" if rag_context else "")
            + "Summarize the situation and the single most important action."
        )
        return await self.execute(system, user, temperature=0.3)

    async def draft_negotiation_strategy(
        self,
        supplier_id: str,
        contract_penalties: List[Dict[str, Any]],
        performance_data: Dict[str, Any],
        tenant_id: str = "default_tenant",
    ) -> AgentResponse:
        """
        Negotiation brief using contract penalty clauses and measured OTP data.
        RAG retrieves historical supplier performance and past SLA terms.
        """
        rag_context = _get_rag_context(
            query=f"supplier {supplier_id} performance delivery SLA contract",
            tenant_id=tenant_id,
            source_types=["supplier_profiles", "carrier_performance", "sla_contract"],
        )
        system = (
            "You are a Chief Procurement Officer. "
            "Draft a supplier negotiation strategy using the performance data and contractual leverage below. "
            "Structure: (1) Leverage Points, (2) Proposed Terms, (3) Walkaway Position. "
            "Be specific and data-driven. No fluff."
        )
        user = (
            f"Supplier: {supplier_id}\n"
            f"Performance: {performance_data}\n"
            f"Contract Penalties: {contract_penalties}\n"
            + (f"\nHistorical context:\n{rag_context}" if rag_context else "")
        )
        content = await self.execute(system, user, temperature=0.2)
        return AgentResponse(
            agent_name="Negotiator",
            content=content,
            suggested_actions=[
                "Send negotiation brief to supplier contact",
                "Update SLA penalty terms in contract database",
                "Schedule review in 30 days",
            ],
            metadata={"supplier_id": supplier_id},
        )

    async def comprehensive_logistics_analysis(
        self, efi_data: Dict[str, Any], context: str
    ) -> AgentResponse:
        """
        Full-spectrum logistics crisis analysis. Called by CopilotService.
        """
        system = (
            "You are a World-Class Supply Chain Strategist. "
            "Analyze the financial data and crisis context. "
            "Provide a structured briefing: "
            "(1) Situation — what is happening and why. "
            "(2) Financial Impact — quantified in USD from the data. "
            "(3) Recommended Action — single most valuable intervention. "
            "3 sentences max per section. Use only the figures given."
        )
        user = f"Crisis: {context}\nFinancial data: {efi_data}"
        content = await self.execute(system, user, temperature=0.2)
        return AgentResponse(
            agent_name="Logistics Strategist",
            content=content,
            suggested_actions=["Execute recommended reroute", "Flag for CFO review"],
            metadata={"context": context},
        )

    async def translate_gnn_risk(
        self, causality: Dict[str, Any], shipment_id: str
    ) -> AgentResponse:
        """
        Turns GNN contagion math into a plain-English story.
        Called when GNN propagation scores are available.
        """
        drivers = causality.get("primary_drivers", [])
        system = (
            "You are a Graph Intelligence Specialist explaining supply chain contagion to a logistics manager. "
            "Describe how risk is flowing between nodes using plain language — no math jargon like 'PageRank' or 'weights'. "
            "Use physical metaphors: 'the delay at Port X is spreading to downstream carriers because...'. "
            "2-3 sentences maximum."
        )
        user = (
            f"Shipment {shipment_id} risk increased due to network propagation.\n"
            f"Topology drivers: {drivers}"
        )
        content = await self.execute(system, user, temperature=0.3)
        return AgentResponse(
            agent_name="GNN Explainer",
            content=content,
            suggested_actions=["Isolate affected downstream nodes", "Alert carrier network"],
            metadata={"shipment_id": shipment_id, "drivers": drivers},
        )

    async def interpret_spatial_risk(
        self,
        h3_id: str,
        risk_context: List[str],
        telemetry: Dict[str, Any],
    ) -> AgentResponse:
        """
        Translates H3 hexagonal grid risk state into tactical plain-language advice.
        Called by CopilotService.analyze_shipment_position().
        """
        context_str = "\n".join(risk_context)
        system = (
            "You are a Spatial Intelligence Analyst for a global logistics platform. "
            "Explain the current location risk in simple, tactical language. "
            "Avoid coordinates and hex IDs — describe zones and threats in plain terms. "
            "End with one clear recommended action."
        )
        user = (
            f"Current zone: {h3_id}\n"
            f"Local risk signals:\n{context_str}\n"
            f"Live telemetry: {telemetry}"
        )
        content = await self.execute(system, user, temperature=0.2)
        return AgentResponse(
            agent_name="Spatial Analyst",
            content=content,
            suggested_actions=["Divert to adjacent safe zone", "Alert port authorities"],
            metadata={"h3_id": h3_id},
        )

    async def get_integrated_copilot_advice(
        self,
        h3_id: str,
        risk_context: List[str],
        efi_data: Dict[str, Any],
        doc_status: str,
    ) -> AgentResponse:
        """
        Fused spatial + financial + document brief.
        Strict 3-tier structure so the frontend can parse sections reliably.
        """
        context_str = "\n".join(risk_context)
        system = (
            "You are the Fiscalogix Logistics Copilot. "
            "Your response MUST follow this exact structure with these exact headers:\n\n"
            "HEADLINE: Estimated Financial Impact: $[amount from data]\n\n"
            "BREAKDOWN:\n"
            "- Delay cost: $[amount]\n"
            "- SLA penalty: $[amount]\n"
            "- Inventory holding: $[amount]\n"
            "- Opportunity cost (WACC): $[amount]\n\n"
            "DECISION: Recommended action: [action]. "
            "This reduces estimated loss to $[new amount] ([X]% improvement).\n\n"
            "Use ONLY figures from the data provided. Do not invent numbers."
        )
        user = (
            f"Zone: {h3_id}\n"
            f"Spatial risks:\n{context_str}\n"
            f"Financial data: {efi_data}\n"
            f"Document status: {doc_status}"
        )
        content = await self.execute(system, user, temperature=0.1)
        return AgentResponse(
            agent_name="Executive Copilot",
            content=content,
            suggested_actions=["Execute reroute", "Issue delay penalty notice to carrier"],
            metadata={"efi_headline": efi_data.get("total_revm")},
        )

    async def analyze_visual_evidence(
        self,
        image_data: str,
        context: str,
        task_type: str = "anomaly_detection",
    ) -> AgentResponse:
        """
        Vision analysis stub. When image_data is a base64 string,
        this will pass it to a vision-capable model.
        Currently processes textual description of the image.
        """
        system = (
            "You are a Logistics Inspector analyzing evidence of cargo damage or disruption. "
            "Be precise. Identify the physical risk, its severity, and one recommended action."
        )
        user = f"Task: {task_type}\nContext: {context}\nImage evidence: {image_data[:500]}"
        content = await self.execute(system, user, temperature=0.1)
        return AgentResponse(
            agent_name="Vision Analyst",
            content=content,
            suggested_actions=["Flag for insurance claim", "Reroute to repair hub"],
            metadata={"task_type": task_type},
        )

    async def extract_document_fields(
        self, text: str, doc_type: str
    ) -> Dict[str, Any]:
        """
        Structured extraction from logistics documents.
        Called by DocumentIntelligenceService.
        Returns a dict that is validated against guardrails before use.
        """
        schemas = {
            "CONTRACT": """{
  "penalty_rate_per_day_pct": <float, e.g. 0.05 for 5%/day, null if not found>,
  "penalty_cap_pct": <float, max penalty as % of order value, null if not found>,
  "payment_terms_days": <int, e.g. 30, null if not found>,
  "incoterms": <string, e.g. "CIF" or "FOB", null if not found>,
  "force_majeure_clause": <bool, null if not found>,
  "governing_law": <string, e.g. "English Law", null if not found>
}""",
            "INVOICE": """{
  "invoice_number": <string>,
  "invoice_date": <string ISO8601>,
  "total_amount_usd": <float>,
  "line_items": [{"description": <string>, "quantity": <int>, "unit_price": <float>}],
  "payment_due_date": <string ISO8601, null if not found>
}""",
            "PERMIT": """{
  "permit_number": <string>,
  "issuing_authority": <string>,
  "expiry_date": <string ISO8601>,
  "permit_scope": [<string>],
  "restricted_goods": [<string>]
}""",
            "BILL_OF_LADING": """{
  "bol_number": <string>,
  "shipper": <string>,
  "consignee": <string>,
  "port_of_loading": <string>,
  "port_of_discharge": <string>,
  "total_weight_kg": <float, null if not found>,
  "container_count": <int, null if not found>
}""",
        }
        schema = schemas.get(doc_type, schemas["BILL_OF_LADING"])
        system = (
            f"You are a logistics document parser extracting {doc_type} data. "
            f"Return ONLY valid JSON matching this exact schema:\n{schema}\n"
            "If a field is not found in the document, use null. "
            "Do not include any text outside the JSON object."
        )
        import json
        result = await self.execute(system, f"Document text:\n{text[:8000]}", temperature=0.0)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            # LLM returned text with JSON embedded — try to extract it
            import re
            match = re.search(r"\{.*\}", result, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            logger.warning(f"LlmGateway.extract_document_fields: JSON parse failed for doc_type={doc_type}")
            return {}

    async def classify_document(self, text: str, filename: str) -> str:
        """
        Classifies a logistics document into one of the known types.
        Returns one of: CONTRACT, INVOICE, PERMIT, BILL_OF_LADING, UNKNOWN
        """
        system = (
            "You are a document classifier for a logistics platform. "
            "Classify the document into exactly one of these types: "
            "CONTRACT, INVOICE, PERMIT, BILL_OF_LADING, UNKNOWN. "
            "Return ONLY the type string. Nothing else."
        )
        user = f"Filename: {filename}\nFirst 1000 chars:\n{text[:1000]}"
        result = await self.execute(system, user, temperature=0.0)
        valid = {"CONTRACT", "INVOICE", "PERMIT", "BILL_OF_LADING", "UNKNOWN"}
        classification = result.strip().upper()
        return classification if classification in valid else "UNKNOWN"

    def discover_erp_mapping(self, raw_headers: List[str]) -> Dict[str, str]:
        """
        Maps raw ERP CSV headers to Fiscalogix schema fields.
        Uses the real LLM synchronously — called once at ingestion time, not per-row.
        Falls back to UNMAPPED_DISCARD if LLM is offline.
        """
        import json
        fiscalogix_fields = [
            "po_number", "origin_node", "destination_node", "current_status",
            "total_value_usd", "expected_arrival_utc", "node_id", "sku_id",
            "quantity_on_hand", "quantity_in_transit", "safety_stock_level",
            "supplier_id", "supplier_name", "financial_health_score",
            "on_time_delivery_rate", "geopolitical_risk_index", "carrier",
            "route", "delay_days", "credit_days",
        ]
        system = (
            "You are a data engineer mapping ERP CSV headers to a logistics schema. "
            f"Map each input header to the best matching field from this list:\n{fiscalogix_fields}\n"
            "Return ONLY valid JSON: {\"<raw_header>\": \"<mapped_field_or_UNMAPPED_DISCARD>\"}. "
            "Use UNMAPPED_DISCARD when nothing fits."
        )
        user = f"Headers to map: {raw_headers}"
        result = self.execute_sync(system, user, temperature=0.0)
        try:
            mapping = json.loads(result)
            # Validate all keys are present
            for h in raw_headers:
                if h not in mapping:
                    mapping[h] = "UNMAPPED_DISCARD"
            return mapping
        except (json.JSONDecodeError, TypeError):
            logger.warning("LlmGateway.discover_erp_mapping: JSON parse failed, returning all UNMAPPED.")
            return {h: "UNMAPPED_DISCARD" for h in raw_headers}
