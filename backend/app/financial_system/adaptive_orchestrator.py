"""
AdaptiveOrchestrator — event-driven pipeline replacing the God-Function.

BEFORE (the problem):
  run() was a single 80-line async function mixing:
    - ML inference         (compute concern)
    - Business logic       (decision concern)
    - LLM orchestration    (AI concern)
    - DB side effects      (persistence concern)
    - Response assembly    (presentation concern)

  Consequence: GNN failure could silently corrupt the ReVM calculation.
  Any exception at step N aborted steps N+1 through end.
  Impossible to test stages in isolation.

AFTER (this file):
  run() is 8 lines — it creates a PipelineContext and delegates to PipelineRunner.

  Each concern lives in its own PipelineStage:
    1. DataIngestionStage       — load + normalize
    2. MLInferenceStage         — delay + demand batch inference
    3. CLVCalibrationStage      — per-account CLV enrichment
    4. DecisionStage            — per-row deterministic decision
    5. SituationAssessmentStage — portfolio heuristics (< 1ms, no LLM)
    6. DispatchPlanningStage    — LLM agent selection (temp=0, deterministic)
    7. AgentExecutionStage      — runs selected agents
    8. PersistenceStage         — audit log + snapshot + decision log

  PipelineRunner guarantees: a failure in stage N is caught, logged, and
  stored as a failed StageOutput. Stage N+1 always executes.
  ctx.result("stage_name") returns {} safely when a stage failed.

Backward compatibility:
  _build_response() assembles the exact same top-level key shape as the old
  orchestrator. All existing frontend consumers work unchanged.
  New key: "pipeline_health" exposes per-stage timings and failure list.
"""

import logging
from typing import Any, Dict

from app.financial_system.engine import FinancialCoreEngine
from app.financial_system.delay_model import DelayPredictionModel
from app.financial_system.demand_model import DemandPredictionModel
from app.financial_system.risk_engine import RiskEngine
from app.financial_system.time_model import TimeValueModel
from app.financial_system.future_model import FutureImpactModel
from app.financial_system.fx_model import FXRiskModel
from app.financial_system.sla_model import SLAPenaltyModel
from app.financial_system.aggregator import FinancialAggregator
from app.financial_system.audit_logger import AuditLogger
from app.financial_system.decision_engine import DecisionEngine
from app.financial_system.cashflow.orchestrator import CashflowPredictorOrchestrator
from app.financial_system.executive.confidence_engine import ConfidenceTrustEngine
from app.financial_system.executive.scenario_engine import ScenarioSimulationEngine
from app.financial_system.executive.monte_carlo import MonteCarloEngine
from app.financial_system.executive.buffer_engine import CashBufferEngine
from app.financial_system.executive.liquidity_engine import LiquidityScoreEngine
from app.financial_system.executive.impact_engine import ImpactEngine
from app.financial_system.optimization.orchestrator import ProfitOptimizationOrchestrator
from app.financial_system.optimization.route_optimizer import GeopoliticalRouteOptimizer
from app.financial_system.ai_mapper import AIFieldMapper
from app.financial_system.clv_calibrator import CLVCalibrator
from app.financial_system.revm_snapshot_logger import RevmSnapshotLogger
from app.financial_system.india.gst_compliance import GSTComplianceModel

from app.financial_system.agents.risk_agent import RiskAgent
from app.financial_system.agents.financial_agent import FinancialAgent
from app.financial_system.agents.routing_agent import RoutingAgent
from app.financial_system.agents.anomaly_agent import AnomalyAgent
from app.financial_system.agents.executive_agent import ExecutiveAgent

from app.services.llm_gateway import LlmGateway

from app.financial_system.pipeline.context import PipelineContext
from app.financial_system.pipeline.runner import PipelineRunner
from app.financial_system.cashflow.carrier_gap_engine import CarrierGapEngine
from app.financial_system.concentration_engine import ConcentrationEngine

from app.financial_system.pipeline.stages import (
    DataIngestionStage,
    MLInferenceStage,
    CLVCalibrationStage,
    GSTComplianceStage,
    DecisionStage,
    SituationAssessmentStage,
    DispatchPlanningStage,
    AgentExecutionStage,
    PersistenceStage,
)

logger = logging.getLogger(__name__)


class AdaptiveOrchestrator:
    """
    Thin coordinator. Owns engine construction and pipeline wiring.
    All execution logic lives in the stages.
    """

    def __init__(self):
        # ── Core deterministic engines ────────────────────────────────────────
        self.core         = FinancialCoreEngine()
        self.delay_model  = DelayPredictionModel()
        self.demand_model = DemandPredictionModel()
        self.risk_engine  = RiskEngine()
        self.time         = TimeValueModel()
        self.future       = FutureImpactModel()
        self.fx           = FXRiskModel()
        self.sla          = SLAPenaltyModel()
        self.aggregator   = FinancialAggregator()
        self.audit        = AuditLogger()
        self.decision     = DecisionEngine()
        self.cashflow     = CashflowPredictorOrchestrator()
        self.revm_snapshot = RevmSnapshotLogger()
        self.gst_model    = GSTComplianceModel()

        self.confidence  = ConfidenceTrustEngine()
        self.scenario    = ScenarioSimulationEngine(
            self.risk_engine, self.time, self.future, self.cashflow
        )
        self.monte_carlo = MonteCarloEngine()
        self.buffer      = CashBufferEngine()
        self.liquidity   = LiquidityScoreEngine()
        self.impact      = ImpactEngine()

        self.route_optimizer = GeopoliticalRouteOptimizer(risk_aversion_beta=3.5)
        self._seed_geopolitical_graph()

        self.poe = ProfitOptimizationOrchestrator(
            self.risk_engine, self.time, self.future,
            route_optimizer=self.route_optimizer,
        )

        # ── Freight-specific analytics ────────────────────────────────────────
        self.carrier_gap   = CarrierGapEngine()
        self.concentration = ConcentrationEngine()

        # ── Intelligence layer ────────────────────────────────────────────────
        self.llm = LlmGateway()

        self._agents = {
            "risk":      RiskAgent(self.risk_engine),
            "financial": FinancialAgent(
                self.time, self.future, self.fx, self.sla,
                self.aggregator, self.monte_carlo, self.cashflow,
            ),
            "routing":   RoutingAgent(self.route_optimizer, self.poe),
            "anomaly":   AnomalyAgent(),
            "executive": ExecutiveAgent(
                self.llm, self.confidence, self.buffer,
                self.liquidity, self.impact, self.scenario,
            ),
        }

        # ── Pipeline wired once at startup — stages are stateless ─────────────
        self._runner = PipelineRunner([
            DataIngestionStage(self.core, AIFieldMapper),
            MLInferenceStage(self.delay_model, self.demand_model),
            CLVCalibrationStage(CLVCalibrator),
            GSTComplianceStage(self.gst_model),
            DecisionStage(self.decision),
            SituationAssessmentStage(self.route_optimizer),
            DispatchPlanningStage(self.llm),
            AgentExecutionStage(self._agents),
            PersistenceStage(self.audit, self.revm_snapshot),
        ])

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC ENTRY POINT — 8 lines
    # ─────────────────────────────────────────────────────────────────────────

    async def run(self, tenant_id: str = "default_tenant") -> Dict[str, Any]:
        """
        Execute the pipeline and return a backward-compatible response dict.
        Never raises — if DataIngestionStage fails (no data), returns {}.
        """
        ctx = PipelineContext(tenant_id=tenant_id)
        ctx = await self._runner.execute(ctx)

        if not ctx.data and ctx.failed("data_ingestion"):
            logger.warning(
                f"[Orchestrator] DataIngestion failed for tenant='{tenant_id}' — returning empty."
            )
            return {}

        return self._build_response(ctx)

    # ─────────────────────────────────────────────────────────────────────────
    # RESPONSE BUILDER — reads context, assembles payload, zero logic
    # ─────────────────────────────────────────────────────────────────────────

    def _build_response(self, ctx: PipelineContext) -> Dict[str, Any]:
        agent_exec    = ctx.result("agent_execution")
        agent_results = agent_exec.get("agent_results", {})

        fin_r    = agent_results.get("FinancialAgent")
        exec_r   = agent_results.get("ExecutiveAgent")
        route_r  = agent_results.get("RoutingAgent")

        fin_data   = fin_r.data   if (fin_r   and fin_r.success)   else {}
        exec_data  = exec_r.data  if (exec_r  and exec_r.success)  else {}
        route_data = route_r.data if (route_r and route_r.success) else {}

        cashflow  = fin_data.get("cashflow", {})
        situation = ctx.result("situation_assessment")
        dispatch  = ctx.result("dispatch_planning")

        # ── Freight-specific analytics (non-blocking) ─────────────────────────
        try:
            carrier_gap_data = self.carrier_gap.compute(ctx.data)
        except Exception as e:
            logger.warning(f"[Orchestrator] CarrierGapEngine failed: {e}")
            carrier_gap_data = {}

        try:
            concentration_data = self.concentration.compute(ctx.data)
        except Exception as e:
            logger.warning(f"[Orchestrator] ConcentrationEngine failed: {e}")
            concentration_data = {}

        return {
            # ── Backward-compatible keys (unchanged shape) ────────────────────
            "summary":            fin_data.get("summary", {}),
            "revm":               ctx.data,
            "cashflow_predictor": cashflow,
            "shocks":             exec_data.get("shocks", cashflow.get("shocks", [])),
            "poe":                route_data.get("optimization_payload", []),
            "confidence":         {"global_score": exec_data.get("global_confidence", 0.5)},
            "scenario_analysis":  exec_data.get("scenarios", []),
            "stochastic_var":     fin_data.get("var", {}),
            "buffer":             exec_data.get("buffer", {}),
            "liquidity":          {"liquidity_score": exec_data.get("liquidity_score", 0)},
            "financial_impact":   exec_data.get("impact", {}),

            # ── Freight analytics (new — freight company focused) ────────────
            "carrier_gap":        carrier_gap_data,
            "concentration":      concentration_data,

            # ── Intelligence layer (additive) ─────────────────────────────────
            "intelligence": {
                "cfo_brief":     exec_data.get("narrative", "[LLM_OFFLINE] Brief unavailable."),
                "dispatch_plan": dispatch.get("plan", []),
                "dispatch_src":  dispatch.get("source", "unknown"),
                "situation":     situation,
                "agent_results": {
                    name: {
                        "success":    r.success,
                        "elapsed_ms": r.elapsed_ms,
                        "error":      r.error or None,
                    }
                    for name, r in agent_results.items()
                    if hasattr(r, "success")
                },
            },

            # ── Pipeline observability (new) ──────────────────────────────────
            # Surfaces per-stage timings + failed stages to the Admin UI.
            # Ops can see "clv_calibration failed, 0 accounts enriched" in the
            # Governance Shield without having to dig into server logs.
            "pipeline_health": {
                "timings_ms":    ctx.timing_summary(),
                "failed_stages": ctx.failed_stages(),
                "total_ms":      round(ctx.total_elapsed_ms(), 1),
            },
        }

    # ─────────────────────────────────────────────────────────────────────────
    # ONE-TIME SETUP (unchanged from previous version)
    # ─────────────────────────────────────────────────────────────────────────

    def _seed_geopolitical_graph(self):
        ro = self.route_optimizer
        for node, t in [
            ("CN", "Friendly"), ("SG", "Friendly"), ("ADEN", "Enemy"),
            ("SUEZ", "Neutral"), ("EU", "Friendly"), ("CAPE", "Friendly"),
            ("US", "Friendly"), ("HUB_A", "Friendly"), ("HUB_B", "Friendly"),
            ("RETAILER_X", "Friendly"),
        ]:
            ro.add_node(node, territory_type=t)

        ro.add_edge("CN",   "SG",          2600,  1.1, 45,  500)
        ro.add_edge("SG",   "ADEN",        6200,  1.1, 45, 1000)
        ro.add_edge("ADEN", "SUEZ",        2400,  1.1, 45, 4500)
        ro.add_edge("SUEZ", "EU",          5800,  1.1, 45, 2000)
        ro.add_edge("SG",   "CAPE",       11500,  1.1, 45, 1200)
        ro.add_edge("CAPE", "EU",         11200,  1.1, 45, 1200)
        ro.add_edge("CN",   "US",         11000,  1.4, 60, 3000, transport_mode="Ocean")
        ro.add_edge("EU",   "HUB_A",        500,  1.0, 30,   50, transport_mode="Truck")
        ro.add_edge("EU",   "HUB_B",        600,  2.0, 60,  500, transport_mode="Rail")
        ro.add_edge("HUB_A","RETAILER_X",   100,  1.0, 30,   20, transport_mode="Truck")
        ro.add_edge("HUB_B","RETAILER_X",   150,  1.0, 30,   20, transport_mode="Truck")
        ro.set_strike("EU", "HUB_A", active=True)
        self.risk_engine.set_contagion_context(ro.graph)
