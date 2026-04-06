"""
ExecutiveAgent — synthesizes all prior agent results into a CFO-ready brief.

This is the ONLY agent that calls the LLM. It receives the deterministic
outputs of every other agent as locked-in facts, then asks Claude to write
plain-language prose explaining those facts.

The LLM cannot change any number. It can only narrate them.
Temperature = 0.3 for this agent (slight variation in prose is acceptable).
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent


_SYSTEM_PROMPT = """You are the AI CFO Advisor for Fiscalogix, a supply chain financial intelligence platform.

Your job is to write an executive brief that a CFO can read in 60 seconds.

STRICT RULES:
1. Use ONLY the figures provided in the data. Never invent, estimate, or approximate numbers.
2. Structure your response with exactly these four sections using these exact headers:
   SITUATION, KEY RISK, RECOMMENDED ACTION, FINANCIAL IMPACT
3. Each section: 2-3 sentences maximum.
4. Tone: Direct, confident, board-room ready. No hedging language ("may", "could", "might").
5. When disruptions are active, name them specifically.
6. End with one clear, single recommended action for the CFO to take right now.
"""


class ExecutiveAgent(BaseAgent):
    name = "ExecutiveAgent"

    def __init__(self, llm_gateway, confidence_engine, buffer_engine,
                 liquidity_engine, impact_engine, scenario_engine):
        super().__init__()
        self._llm        = llm_gateway
        self._confidence = confidence_engine
        self._buffer     = buffer_engine
        self._liquidity  = liquidity_engine
        self._impact     = impact_engine
        self._scenario   = scenario_engine

    async def run_logic(
        self,
        enriched_data: List[Dict[str, Any]],
        prior_results: Dict[str, Any],
        tenant_id: str,
    ) -> Dict[str, Any]:
        # Pull deterministic outputs from prior agents
        fin   = prior_results.get("FinancialAgent")
        risk  = prior_results.get("RiskAgent")
        route = prior_results.get("RoutingAgent")
        anom  = prior_results.get("AnomalyAgent")

        fin_data   = fin.data   if fin   and fin.success   else {}
        risk_data  = risk.data  if risk  and risk.success  else {}
        route_data = route.data if route and route.success else {}
        anom_data  = anom.data  if anom  and anom.success  else {}

        cashflow = fin_data.get("cashflow", {})
        shocks   = cashflow.get("shocks", [])

        # Compute executive metrics — all deterministic
        global_confidence = self._confidence.compute(enriched_data, shocks)
        liquidity_score   = self._liquidity.compute(
            fin_data.get("ending_cash", 0),
            cashflow.get("timeline", []),
            shocks,
            enriched_data,
        )
        buffer_rec = self._buffer.compute(
            fin_data.get("peak_deficit", 0),
            shocks,
            global_confidence,
        )
        impact_metrics = self._impact.compute(
            enriched_data,
            route_data.get("optimization_payload", []),
            fin_data.get("var", {}),
        )

        # Scenario simulations — deterministic stress tests
        scen_delay  = self._scenario.simulate(enriched_data, "delay +2 days",   delay_shift=2)
        scen_demand = self._scenario.simulate(enriched_data, "demand drop -5%", demand_shift_pct=-0.05)

        # ── RAG context for the brief ─────────────────────────────────────────
        try:
            from app.services.rag import get_retriever
            rag_query = (
                f"executive summary portfolio risk "
                f"{'disruption ' + ' '.join(route_data.get('active_disruptions', [])) if route_data.get('disruption_count', 0) > 0 else ''}"
            )
            rag_context = get_retriever().get_context(
                rag_query, tenant_id,
                source_types=["route_performance", "carrier_performance", "decision_outcomes"],
            )
        except Exception:
            rag_context = ""

        # ── Build the locked-in facts payload for the LLM ────────────────────
        total_revm        = fin_data.get("total_revm", 0)
        var_95            = fin_data.get("var_95", 0)
        high_risk_count   = risk_data.get("high_risk_count", 0)
        critical_count    = risk_data.get("critical_count", 0)
        disruptions       = route_data.get("active_disruptions", [])
        anomaly_count     = anom_data.get("anomaly_count", 0)
        top_anomalies     = anom_data.get("anomalies", [])[:3]
        recommendations   = route_data.get("recommendations", [])

        facts = (
            f"Portfolio ReVM: ${total_revm:,.0f}\n"
            f"Value at Risk (95% confidence): ${var_95:,.0f}\n"
            f"High-risk shipments: {high_risk_count} | Critical: {critical_count}\n"
            f"System confidence score: {global_confidence:.0%}\n"
            f"Liquidity score: {liquidity_score:.2f}\n"
            f"Recommended cash buffer: ${buffer_rec.get('recommended_buffer', 0):,.0f}\n"
            f"Active disruptions: {', '.join(disruptions) if disruptions else 'None'}\n"
            f"Statistical anomalies detected: {anomaly_count}\n"
            + (f"Top anomalies: {top_anomalies}\n" if top_anomalies else "")
            + (f"Recommended actions: {', '.join(recommendations[:3])}\n" if recommendations else "")
            + (f"\nHistorical context:\n{rag_context}\n" if rag_context else "")
        )

        # ── LLM narrative synthesis ───────────────────────────────────────────
        narrative = await self._llm.execute(
            system=_SYSTEM_PROMPT,
            user=f"Current portfolio data:\n{facts}",
            temperature=0.3,
        )

        return {
            "narrative":          narrative,
            "global_confidence":  global_confidence,
            "liquidity_score":    liquidity_score,
            "buffer":             buffer_rec,
            "impact":             impact_metrics,
            "scenarios":          [scen_delay, scen_demand],
            "shocks":             shocks,
            "total_revm":         total_revm,
            "var_95":             var_95,
        }
