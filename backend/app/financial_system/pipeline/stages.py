"""
Pipeline stages — each encapsulates exactly one responsibility.

Rules every stage must follow:
  1. Accept only what it needs in __init__ (injected by orchestrator).
  2. Read prior stages via ctx.result("stage_name") — never access
     ctx.stage_outputs directly.
  3. Enrich ctx.data rows by STAMPING new keys — never delete existing ones.
  4. Return a plain dict that becomes StageOutput.data.
  5. Raise on unrecoverable errors — the runner handles isolation.
     Use logger.warning for expected degradations (missing models, etc.).

Stage execution order (enforced by orchestrator):
  1. DataIngestionStage      → populates ctx.data
  2. MLInferenceStage        → stamps predicted_delay, predicted_demand
  3. CLVCalibrationStage     → stamps clv_calibration
  4. DecisionStage           → stamps decision
  5. SituationAssessmentStage → pure heuristics, no LLM
  6. DispatchPlanningStage   → LLM agent selection
  7. AgentExecutionStage     → runs selected agents
  8. PersistenceStage        → audit log + ReVM snapshot + decision log
"""

from __future__ import annotations

import json
import logging
import statistics
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.financial_system.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# BASE
# ─────────────────────────────────────────────────────────────────────────────

class PipelineStage(ABC):
    """
    Every stage has a unique name (used as the key in ctx.stage_outputs)
    and an execute() method that receives the shared context.
    """
    name: str

    @abstractmethod
    def execute(self, ctx: PipelineContext) -> Dict[str, Any]:
        """
        Sync execute — override with `async def execute` if the stage needs
        to await (e.g. LLM calls). PipelineRunner handles both transparently.
        """
        ...


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — Data Ingestion + Normalization
# ─────────────────────────────────────────────────────────────────────────────

class DataIngestionStage(PipelineStage):
    """
    Responsibility: Load raw shipment records from the DB and normalize
    field taxonomy so downstream stages speak a consistent column language.

    Failure: Raises ValueError if the tenant has zero records (nothing to do).
    This is the ONLY stage whose failure aborts the pipeline — every other
    stage can degrade gracefully, but without data there is nothing to process.
    """
    name = "data_ingestion"

    def __init__(self, core, ai_mapper_cls):
        self._core   = core
        self._mapper = ai_mapper_cls

    def execute(self, ctx: PipelineContext) -> Dict[str, Any]:
        raw = self._core.compute(tenant_id=ctx.tenant_id)
        if not raw:
            raise ValueError(
                f"DataIngestionStage: no records found for tenant='{ctx.tenant_id}'"
            )
        ctx.data = [self._mapper.normalize_row_taxonomy(row) for row in raw]
        return {"record_count": len(ctx.data)}


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — Batch ML Inference (Delay + Demand)
# ─────────────────────────────────────────────────────────────────────────────

class MLInferenceStage(PipelineStage):
    """
    Responsibility: Run delay and demand batch predictions in one pass.
    Stamps predicted_delay and predicted_demand onto each row.

    Degradation: If either model is in heuristic fallback, values are still
    valid (just less accurate). The stage never fails on fallback mode.
    """
    name = "ml_inference"

    def __init__(self, delay_model, demand_model):
        self._delay  = delay_model
        self._demand = demand_model

    def execute(self, ctx: PipelineContext) -> Dict[str, Any]:
        delays  = self._delay.compute_batch(ctx.data)
        demands = self._demand.compute_batch(ctx.data)

        for i, row in enumerate(ctx.data):
            row["predicted_delay"]  = delays[i]
            row["predicted_demand"] = demands[i]

        delay_model_mode  = "ml"  if getattr(self._delay,  "model", None) else "heuristic"
        demand_model_mode = "ml"  if getattr(self._demand, "model", None) else "heuristic"

        return {
            "delay_model_mode":  delay_model_mode,
            "demand_model_mode": demand_model_mode,
            "records_scored":    len(ctx.data),
        }


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 3 — CLV Calibration
# ─────────────────────────────────────────────────────────────────────────────

class CLVCalibrationStage(PipelineStage):
    """
    Responsibility: Enrich each row with per-account CLV calibration data
    (repeat-purchase ratio, churn probability) derived from shipment history.

    Degradation: If DB is unavailable or CLVCalibrator raises, all rows get
    clv_calibration=None. FutureImpactModel falls back to tier multipliers.
    This is a non-fatal enrichment — the stage logs a warning and returns.
    """
    name = "clv_calibration"

    def __init__(self, calibrator_cls):
        self._calibrator_cls = calibrator_cls

    def execute(self, ctx: PipelineContext) -> Dict[str, Any]:
        calibrator    = self._calibrator_cls()
        calibrations  = calibrator.calibrate_batch(ctx.data, tenant_id=ctx.tenant_id)
        enriched      = 0

        for row in ctx.data:
            cid = str(row.get("customer_id", "")).strip()
            row["clv_calibration"] = calibrations.get(cid)
            if row["clv_calibration"] is not None:
                enriched += 1

        return {
            "accounts_calibrated": enriched,
            "accounts_fallback":   len(ctx.data) - enriched,
        }


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 4 — Per-Row Decision Engine
# ─────────────────────────────────────────────────────────────────────────────

class DecisionStage(PipelineStage):
    """
    Responsibility: Run deterministic decision logic per row (REROUTE / MONITOR /
    PROCEED). Stamps the 'decision' key.

    This stage depends on ML outputs (predicted_delay, predicted_demand) being
    already on the rows. If MLInferenceStage failed, rows have no predicted_delay
    so the decision engine falls back to defaults internally — still produces
    a valid (conservative) decision.
    """
    name = "decision"

    def __init__(self, decision_engine):
        self._engine = decision_engine

    def execute(self, ctx: PipelineContext) -> Dict[str, Any]:
        for row in ctx.data:
            row["decision"] = self._engine.compute(row)

        decisions = [r.get("decision", {}) for r in ctx.data]
        reroute_count = sum(
            1 for d in decisions if isinstance(d, dict) and d.get("action") == "REROUTE"
        )
        return {
            "reroute_count":  reroute_count,
            "total_decisions": len(ctx.data),
        }


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 5 — Situation Assessment (pure heuristics, no LLM)
# ─────────────────────────────────────────────────────────────────────────────

class SituationAssessmentStage(PipelineStage):
    """
    Responsibility: Derive portfolio-level signals that the LLM dispatcher
    uses to select agents. Pure Python — no ML inference, no network calls.
    Runs in < 1ms regardless of portfolio size.

    Output feeds directly into DispatchPlanningStage as the LLM user message.
    """
    name = "situation_assessment"

    def __init__(self, route_optimizer):
        self._route_optimizer = route_optimizer

    def execute(self, ctx: PipelineContext) -> Dict[str, Any]:
        data         = ctx.data
        delays       = [r.get("predicted_delay", 0) for r in data]
        risk_scores  = [r.get("risk_score", 0.05)   for r in data]
        order_values = [r.get("order_value", 0)      for r in data]

        high_risk  = sum(1 for s in risk_scores if s > 0.65)
        critical   = sum(1 for s in risk_scores if s > 0.85)

        active_strikes   = False
        disruption_count = 0
        try:
            for _, _, edata in self._route_optimizer.graph.edges(data=True):
                if edata.get("strike_active"):
                    active_strikes = True
                    disruption_count += 1
            for _, ndata in self._route_optimizer.graph.nodes(data=True):
                if ndata.get("territory_type") == "Enemy":
                    disruption_count += 1
        except Exception:
            pass  # Graph not seeded yet — safe to ignore

        sigma_breach = False
        if len(delays) > 3:
            try:
                mean_d  = statistics.mean(delays)
                stdev_d = statistics.stdev(delays) or 1e-9
                sigma_breach = max(abs(d - mean_d) / stdev_d for d in delays) > 2.0
            except Exception:
                pass

        return {
            "total_records":    len(data),
            "high_risk_count":  high_risk,
            "critical_count":   critical,
            "total_exposure":   round(sum(order_values), 0),
            "active_strikes":   active_strikes,
            "disruption_count": disruption_count,
            "sigma_breach":     sigma_breach,
            "avg_risk_score":   round(sum(risk_scores) / max(len(risk_scores), 1), 3),
        }


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 6 — LLM Dispatch Planning
# ─────────────────────────────────────────────────────────────────────────────

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

_ALL_AGENTS = {"risk", "financial", "routing", "anomaly", "executive"}


class DispatchPlanningStage(PipelineStage):
    """
    Responsibility: Ask the LLM which agents to run given the situation.
    temperature=0 makes this deterministic for identical inputs.

    Degradation: If the LLM is offline or returns malformed JSON, falls back
    to a deterministic heuristic plan derived from the situation dict.
    The pipeline always gets a valid plan — never an empty list.
    """
    name = "dispatch_planning"

    def __init__(self, llm_gateway):
        self._llm = llm_gateway

    async def execute(self, ctx: PipelineContext) -> Dict[str, Any]:
        situation = ctx.result("situation_assessment")
        user_msg  = f"Portfolio situation: {json.dumps(situation)}"

        plan = None
        source = "llm"

        try:
            raw  = await self._llm.execute(_DISPATCH_SYSTEM, user_msg, temperature=0.0)
            plan = self._parse_plan(raw)
        except Exception as e:
            logger.warning(f"[DispatchPlanningStage] LLM unavailable ({e}) — using heuristic plan")

        if plan is None:
            plan   = self._heuristic_plan(situation)
            source = "heuristic"

        return {"plan": plan, "source": source}

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_plan(raw: str) -> Optional[List[str]]:
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            return None
        valid = [a for a in parsed if a in _ALL_AGENTS]
        # Enforce mandatory bookends
        if "risk"      not in valid: valid.insert(0, "risk")
        if "executive" not in valid: valid.append("executive")
        if valid[-1] != "executive":
            valid.remove("executive")
            valid.append("executive")
        return valid

    @staticmethod
    def _heuristic_plan(situation: Dict[str, Any]) -> List[str]:
        plan = ["risk", "financial"]
        if situation.get("disruption_count", 0) > 0 or situation.get("active_strikes"):
            plan.append("routing")
        if situation.get("sigma_breach") or situation.get("critical_count", 0) > 3:
            plan.append("anomaly")
        plan.append("executive")
        return plan


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 7 — Agent Execution
# ─────────────────────────────────────────────────────────────────────────────

class AgentExecutionStage(PipelineStage):
    """
    Responsibility: Run the agents selected by DispatchPlanningStage.
    Each agent receives ctx.data and the accumulated agent_results dict
    so agents can build on each other's outputs (e.g. ExecutiveAgent
    reads RiskAgent's output to write its CFO brief).

    Degradation: If an individual agent raises, it is skipped and logged.
    The remaining agents always execute. ExecutiveAgent always runs last —
    even if earlier agents failed, it produces a degraded brief.
    """
    name = "agent_execution"

    def __init__(self, agents: Dict[str, Any]):
        self._agents = agents

    async def execute(self, ctx: PipelineContext) -> Dict[str, Any]:
        plan      = ctx.result("dispatch_planning").get("plan", ["risk", "financial", "executive"])
        tenant_id = ctx.tenant_id

        agent_results: Dict[str, Any] = {}
        timings:       Dict[str, float] = {}

        for agent_name in plan:
            agent = self._agents.get(agent_name)
            if agent is None:
                logger.warning(f"[AgentExecutionStage] Unknown agent '{agent_name}' — skipping")
                continue

            import time as _time
            t0 = _time.perf_counter()
            try:
                result = await agent.run(ctx.data, agent_results, tenant_id)
                agent_results[result.agent_name if hasattr(result, "agent_name") else agent.__class__.__name__] = result
            except Exception as exc:
                logger.error(f"[AgentExecutionStage] Agent '{agent_name}' failed: {exc}", exc_info=True)
            finally:
                timings[agent_name] = round((_time.perf_counter() - t0) * 1000, 2)

        return {
            "agent_results": agent_results,
            "agent_timings": timings,
            "agents_run":    list(timings.keys()),
        }


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 8 — Persistence (Audit + Snapshot + Decision Log)
# ─────────────────────────────────────────────────────────────────────────────

class PersistenceStage(PipelineStage):
    """
    Responsibility: Write side effects — audit log, ReVM snapshot, decision log.
    This is deliberately the LAST stage so it never blocks financial computation.

    Degradation: Each write is wrapped independently. A DB outage on the
    audit log must not prevent the decision log from writing, and vice versa.
    All failures are logged at ERROR level but never re-raised.
    """
    name = "persistence"

    def __init__(self, audit_logger, revm_snapshot_logger):
        self._audit    = audit_logger
        self._snapshot = revm_snapshot_logger

    def execute(self, ctx: PipelineContext) -> Dict[str, Any]:
        results = {"audit": False, "snapshot": False, "decision_log": False}

        # 1. Audit log
        try:
            self._audit.log_batch(ctx.data)
            results["audit"] = True
        except Exception as e:
            logger.error(f"[PersistenceStage] AuditLogger failed: {e}", exc_info=True)

        # 2. ReVM snapshot
        try:
            self._snapshot.save_batch(ctx.data, ctx.tenant_id)
            results["snapshot"] = True
        except Exception as e:
            logger.error(f"[PersistenceStage] RevmSnapshotLogger failed: {e}", exc_info=True)

        # 3. Decision log — reads routing agent output
        try:
            agent_results = ctx.result("agent_execution").get("agent_results", {})
            routing_r     = agent_results.get("RoutingAgent")
            payload       = routing_r.data.get("optimization_payload", []) if (routing_r and routing_r.success) else []
            self._write_decision_log(payload, ctx.tenant_id)
            results["decision_log"] = True
        except Exception as e:
            logger.error(f"[PersistenceStage] DecisionLog write failed: {e}", exc_info=True)

        return results

    @staticmethod
    def _write_decision_log(payload: list, tenant_id: str):
        if not payload:
            return
        from setup_db import DecisionLog
        from app.Db.connections import SessionLocal

        db = SessionLocal()
        try:
            entries = [
                DecisionLog(
                    decision_id      = str(uuid.uuid4()),
                    tenant_id        = tenant_id,
                    shipment_id      = d.get("shipment_id"),
                    route_selected   = d.get("action"),
                    predicted_efi    = d.get("expected_efi"),
                    confidence_score = d.get("confidence_score"),
                    risk_posture     = d.get("risk_posture"),
                )
                for d in payload
            ]
            db.bulk_save_objects(entries)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
