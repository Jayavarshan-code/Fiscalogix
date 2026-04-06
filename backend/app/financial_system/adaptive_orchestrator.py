"""
AdaptiveOrchestrator — the reasoning layer that replaces the static pipeline.

Old model (orchestrator.py):
  Always runs: Phase1 → Phase2 → Phase3 → Phase4 in fixed order.
  Every run is identical regardless of what the data shows.

New model (this file):
  1. Load raw data (deterministic — same as before)
  2. Run batch ML inference (deterministic — delay, demand in one pass)
  3. Assess the situation from the data (fast, no LLM)
  4. LLM decides which agents to run and in what order (temperature=0)
  5. Agents execute in the planned order, each reading prior results
  6. ExecutiveAgent synthesizes everything into a CFO brief (temperature=0.3)

Determinism guarantee:
  Steps 1-3 and all agent financial computations are fully deterministic.
  The LLM is involved only in steps 4 (dispatch — temperature=0) and
  6 (narrative — temperature=0.3). The numbers never change.

Backward compatibility:
  The final return dict has the same top-level keys as the old orchestrator
  so existing frontend consumers require no changes.
  New keys are additive: "intelligence", "dispatch_plan", "agent_timings".
"""

import logging
import json
from typing import List, Dict, Any, Optional

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

from app.financial_system.agents.base_agent import AgentResult
from app.financial_system.agents.risk_agent import RiskAgent
from app.financial_system.agents.financial_agent import FinancialAgent
from app.financial_system.agents.routing_agent import RoutingAgent
from app.financial_system.agents.anomaly_agent import AnomalyAgent
from app.financial_system.agents.executive_agent import ExecutiveAgent

from app.services.llm_gateway import LlmGateway

logger = logging.getLogger(__name__)

# All available agent names the LLM dispatcher can select from
ALL_AGENTS = ["risk", "financial", "routing", "anomaly", "executive"]

# Dispatch prompt — temperature=0 makes this deterministic
_DISPATCH_SYSTEM = """You are a supply chain analysis dispatcher for Fiscalogix.
Given the current portfolio situation, return a JSON array of agent names to execute, in order.

Available agents: ["risk", "financial", "routing", "anomaly", "executive"]

Dispatch rules:
- ALWAYS include "risk" first and "executive" last — these are mandatory.
- Include "financial" unless total_records is 0.
- Include "routing" ONLY IF disruption_count > 0 OR active_strikes is true.
- Include "anomaly" ONLY IF sigma_breach is true OR critical_count > 3.
- Return ONLY a valid JSON array. No explanation, no markdown, no extra text.

Examples:
  Calm portfolio, no disruptions → ["risk", "financial", "executive"]
  Strike active, high anomalies  → ["risk", "financial", "routing", "anomaly", "executive"]
"""


class AdaptiveOrchestrator:
    """
    Intelligent replacement for the static FinancialIntelligenceOrchestrator.

    Drop-in: same constructor signature, same run() return shape.
    The intelligence layer is additive — all existing keys are preserved.
    """

    def __init__(self):
        # ── Core deterministic engines (unchanged) ────────────────────────────
        self.core        = FinancialCoreEngine()
        self.delay_model = DelayPredictionModel()
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

        from app.financial_system.revm_snapshot_logger import RevmSnapshotLogger
        self.revm_snapshot = RevmSnapshotLogger()

        self.confidence = ConfidenceTrustEngine()
        self.scenario   = ScenarioSimulationEngine(self.risk_engine, self.time, self.future, self.cashflow)
        self.monte_carlo = MonteCarloEngine()
        self.buffer     = CashBufferEngine()
        self.liquidity  = LiquidityScoreEngine()
        self.impact     = ImpactEngine()

        self.route_optimizer = GeopoliticalRouteOptimizer(risk_aversion_beta=3.5)
        self._seed_geopolitical_graph()

        self.poe = ProfitOptimizationOrchestrator(
            self.risk_engine, self.time, self.future,
            route_optimizer=self.route_optimizer
        )

        # ── Intelligence layer ────────────────────────────────────────────────
        self.llm = LlmGateway()

        self._agents: Dict[str, Any] = {
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

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC ENTRY POINT
    # ─────────────────────────────────────────────────────────────────────────

    async def run(self, tenant_id: str = "default_tenant") -> Dict[str, Any]:
        """
        Main intelligence pipeline. Returns same shape as old orchestrator
        plus new "intelligence" key with CFO brief and agent metadata.
        """
        # Step 1: Load raw data (deterministic)
        raw_data = self.core.compute(tenant_id=tenant_id)
        if not raw_data:
            return {}

        # Step 2: Taxonomy normalisation + batch ML inference (deterministic)
        data = [AIFieldMapper.normalize_row_taxonomy(row) for row in raw_data]
        predicted_delays  = self.delay_model.compute_batch(data)
        predicted_demands = self.demand_model.compute_batch(data)

        # Stamp ML outputs onto rows so agents can read them directly
        for i, row in enumerate(data):
            row["predicted_delay"]  = predicted_delays[i]
            row["predicted_demand"] = predicted_demands[i]

        # Step 3: Decision engine per row (deterministic)
        for row in data:
            row["decision"] = self.decision.compute(row)

        # Step 4: Assess situation from data (no LLM — fast heuristics)
        situation = self._assess_situation(data)
        logger.info(f"[Adaptive] Situation: {situation}")

        # Step 5: LLM dispatch planning (temperature=0 — deterministic for same input)
        dispatch_plan = await self._plan_dispatch(situation)
        logger.info(f"[Adaptive] Dispatch plan: {dispatch_plan}")

        # Step 6: Execute agents in planned order
        results: Dict[str, AgentResult] = {}
        for agent_name in dispatch_plan:
            agent = self._agents.get(agent_name)
            if not agent:
                logger.warning(f"[Adaptive] Unknown agent: {agent_name} — skipping")
                continue
            result = await agent.run(data, results, tenant_id)
            results[agent.__class__.__name__] = result

        # Step 7: Audit + ReVM snapshots (unchanged from old orchestrator)
        try:
            self.audit.log_batch(data)
        except Exception as e:
            logger.error(f"Adaptive: AuditLogger failed — {e}", exc_info=True)

        try:
            self.revm_snapshot.save_batch(data, tenant_id)
        except Exception as e:
            logger.error(f"Adaptive: RevmSnapshotLogger failed — {e}", exc_info=True)

        # Step 8: Persist decision log
        self._log_decisions(
            results.get("RoutingAgent", AgentResult("RoutingAgent", False)).data.get(
                "optimization_payload", []
            ),
            tenant_id,
        )

        # Step 9: Build return payload (backward compatible + new intelligence key)
        return self._build_response(data, results, situation, dispatch_plan)

    # ─────────────────────────────────────────────────────────────────────────
    # SITUATION ASSESSMENT  (pure Python — no LLM, runs in <1ms)
    # ─────────────────────────────────────────────────────────────────────────

    def _assess_situation(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extracts portfolio-level signals used by the LLM dispatcher.
        All heuristics — no ML inference at this stage.
        """
        import statistics

        delays        = [r.get("predicted_delay", 0) for r in data]
        risk_scores   = [r.get("risk_score", 0.05) for r in data]
        order_values  = [r.get("order_value", 0) for r in data]

        high_risk  = sum(1 for s in risk_scores if s > 0.65)
        critical   = sum(1 for s in risk_scores if s > 0.85)
        total_exp  = sum(order_values)

        # Detect active strikes from geopolitical graph
        active_strikes = False
        disruption_count = 0
        try:
            for _, _, edata in self.route_optimizer.graph.edges(data=True):
                if edata.get("strike_active"):
                    active_strikes = True
                    disruption_count += 1
            for _, ndata in self.route_optimizer.graph.nodes(data=True):
                if ndata.get("territory_type") == "Enemy":
                    disruption_count += 1
        except Exception:
            pass

        # Sigma breach check
        sigma_breach = False
        if len(delays) > 3:
            try:
                mean_d = statistics.mean(delays)
                stdev_d = statistics.stdev(delays) or 1e-9
                max_z = max(abs(d - mean_d) / stdev_d for d in delays)
                sigma_breach = max_z > 2.0
            except Exception:
                pass

        return {
            "total_records":    len(data),
            "high_risk_count":  high_risk,
            "critical_count":   critical,
            "total_exposure":   round(total_exp, 0),
            "active_strikes":   active_strikes,
            "disruption_count": disruption_count,
            "sigma_breach":     sigma_breach,
            "avg_risk_score":   round(sum(risk_scores) / max(len(risk_scores), 1), 3),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # LLM DISPATCH PLANNER  (temperature=0 — same situation → same plan)
    # ─────────────────────────────────────────────────────────────────────────

    async def _plan_dispatch(self, situation: Dict[str, Any]) -> List[str]:
        """
        Asks the LLM which agents to run given the situation.
        Falls back to full pipeline if LLM is offline.
        """
        user = f"Portfolio situation: {json.dumps(situation)}"
        raw  = await self.llm.execute(_DISPATCH_SYSTEM, user, temperature=0.0)

        # Parse JSON array from response
        try:
            plan = json.loads(raw)
            if isinstance(plan, list):
                # Validate: only known agent names, executive always last
                valid = [a for a in plan if a in ALL_AGENTS]
                if "risk"      not in valid:   valid.insert(0, "risk")
                if "executive" not in valid:   valid.append("executive")
                if valid[-1] != "executive":
                    valid.remove("executive")
                    valid.append("executive")
                return valid
        except (json.JSONDecodeError, ValueError):
            pass

        # LLM offline or returned bad JSON — deterministic fallback
        logger.warning("[Adaptive] Dispatch planning failed — using full pipeline fallback")
        fallback = ["risk", "financial"]
        if situation.get("disruption_count", 0) > 0 or situation.get("active_strikes"):
            fallback.append("routing")
        if situation.get("sigma_breach") or situation.get("critical_count", 0) > 3:
            fallback.append("anomaly")
        fallback.append("executive")
        return fallback

    # ─────────────────────────────────────────────────────────────────────────
    # RESPONSE BUILDER  (backward-compatible + additive)
    # ─────────────────────────────────────────────────────────────────────────

    def _build_response(
        self,
        data: List[Dict[str, Any]],
        results: Dict[str, AgentResult],
        situation: Dict[str, Any],
        dispatch_plan: List[str],
    ) -> Dict[str, Any]:
        fin_r  = results.get("FinancialAgent")
        exec_r = results.get("ExecutiveAgent")
        route_r = results.get("RoutingAgent")

        fin_data  = fin_r.data  if fin_r  and fin_r.success  else {}
        exec_data = exec_r.data if exec_r and exec_r.success else {}
        route_data = route_r.data if route_r and route_r.success else {}

        cashflow = fin_data.get("cashflow", {})

        return {
            # ── Backward-compatible keys (old orchestrator shape) ─────────────
            "summary":           fin_data.get("summary", {}),
            "revm":              data,
            "cashflow_predictor": cashflow,
            "shocks":            exec_data.get("shocks", cashflow.get("shocks", [])),
            "poe":               route_data.get("optimization_payload", []),
            "confidence":        {"global_score": exec_data.get("global_confidence", 0.5)},
            "scenario_analysis": exec_data.get("scenarios", []),
            "stochastic_var":    fin_data.get("var", {}),
            "buffer":            exec_data.get("buffer", {}),
            "liquidity":         {"liquidity_score": exec_data.get("liquidity_score", 0)},
            "financial_impact":  exec_data.get("impact", {}),

            # ── New intelligence layer keys ───────────────────────────────────
            "intelligence": {
                "cfo_brief":        exec_data.get("narrative", "[LLM_OFFLINE] Brief unavailable."),
                "dispatch_plan":    dispatch_plan,
                "situation":        situation,
                "agent_results":    {
                    name: {
                        "success":    r.success,
                        "elapsed_ms": r.elapsed_ms,
                        "error":      r.error or None,
                    }
                    for name, r in results.items()
                },
            },
        }

    # ─────────────────────────────────────────────────────────────────────────
    # UNCHANGED HELPERS FROM OLD ORCHESTRATOR
    # ─────────────────────────────────────────────────────────────────────────

    def _log_decisions(self, optimized_payload, tenant_id: str = "default_tenant"):
        from setup_db import DecisionLog
        import uuid
        from app.Db.connections import SessionLocal

        if not optimized_payload:
            return

        db = SessionLocal()
        try:
            entries = [
                DecisionLog(
                    decision_id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    shipment_id=d.get("shipment_id"),
                    route_selected=d.get("action"),
                    predicted_efi=d.get("expected_efi"),
                    confidence_score=d.get("confidence_score"),
                    risk_posture=d.get("risk_posture"),
                )
                for d in optimized_payload
            ]
            db.bulk_save_objects(entries)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"_log_decisions failed — {e}", exc_info=True)
        finally:
            db.close()

    def _seed_geopolitical_graph(self):
        """Identical to old orchestrator — seeds the Dijkstra graph."""
        ro = self.route_optimizer
        for node, t in [("CN","Friendly"),("SG","Friendly"),("ADEN","Enemy"),
                        ("SUEZ","Neutral"),("EU","Friendly"),("CAPE","Friendly"),("US","Friendly"),
                        ("HUB_A","Friendly"),("HUB_B","Friendly"),("RETAILER_X","Friendly")]:
            ro.add_node(node, territory_type=t)

        ro.add_edge("CN","SG",2600,1.1,45,500)
        ro.add_edge("SG","ADEN",6200,1.1,45,1000)
        ro.add_edge("ADEN","SUEZ",2400,1.1,45,4500)
        ro.add_edge("SUEZ","EU",5800,1.1,45,2000)
        ro.add_edge("SG","CAPE",11500,1.1,45,1200)
        ro.add_edge("CAPE","EU",11200,1.1,45,1200)
        ro.add_edge("CN","US",11000,1.4,60,3000,transport_mode="Ocean")
        ro.add_edge("EU","HUB_A",500,1.0,30,50,transport_mode="Truck")
        ro.add_edge("EU","HUB_B",600,2.0,60,500,transport_mode="Rail")
        ro.add_edge("HUB_A","RETAILER_X",100,1.0,30,20,transport_mode="Truck")
        ro.add_edge("HUB_B","RETAILER_X",150,1.0,30,20,transport_mode="Truck")
        ro.set_strike("EU","HUB_A",active=True)
        self.risk_engine.set_contagion_context(ro.graph)
