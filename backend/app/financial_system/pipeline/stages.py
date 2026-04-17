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

import gc
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

        valid_rows  = []
        failed_rows = []
        for i, row in enumerate(raw):
            try:
                valid_rows.append(self._mapper.normalize_row_taxonomy(row))
            except Exception as e:
                failed_rows.append({"index": i, "error": str(e)})
                logger.warning(
                    f"[DataIngestionStage] Row {i} normalization failed — skipping: {e}"
                )

        if not valid_rows:
            raise ValueError(
                f"DataIngestionStage: all {len(raw)} rows failed normalization "
                f"for tenant='{ctx.tenant_id}'"
            )

        if failed_rows:
            logger.error(
                f"[DataIngestionStage] {len(failed_rows)}/{len(raw)} rows failed normalization "
                f"for tenant='{ctx.tenant_id}'. Processing {len(valid_rows)} valid rows."
            )

        ctx.data = valid_rows
        return {
            "record_count":        len(valid_rows),
            "failed_row_count":    len(failed_rows),
            "normalization_errors": failed_rows,
        }


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

        # Release XGBoost intermediate arrays before the next stage allocates
        gc.collect()

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
# STAGE 4 — GST Compliance
# ─────────────────────────────────────────────────────────────────────────────

class GSTComplianceStage(PipelineStage):
    """
    Responsibility: Calculate GST impact per row (Imports/Exports) for Indian routes.
    Stamps 'gst_cost', 'gst_breakdown' on rows.
    """
    name = "gst_compliance"

    def __init__(self, gst_model):
        self._gst_model = gst_model

    def execute(self, ctx: PipelineContext) -> Dict[str, Any]:
        total_gst_cost = 0.0
        for row in ctx.data:
            cost = self._gst_model.compute(row)
            row["gst_cost"] = cost
            total_gst_cost += cost

        return {
            "total_gst_cost_computed": round(total_gst_cost, 2),
            "records_processed": len(ctx.data)
        }


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 5 — Per-Row Decision Engine
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
        failed = 0
        for row in ctx.data:
            try:
                row["decision"] = self._engine.compute(row)
            except Exception as e:
                failed += 1
                logger.error(
                    f"[DecisionStage] compute failed for row "
                    f"shipment_id={row.get('shipment_id', '?')}: {e}",
                    exc_info=True,
                )
                row["decision"] = {
                    "action":     "ESCALATE TO MANAGEMENT",
                    "reason":     "Decision engine error — conservative fallback applied.",
                    "drivers":    ["upstream data missing or malformed"],
                    "confidence": 0.0,
                    "revm_pct":   0.0,
                    "tier":       3,
                }

        decisions = [r.get("decision", {}) for r in ctx.data]
        reroute_count = sum(
            1 for d in decisions if isinstance(d, dict) and d.get("action") == "REROUTE"
        )
        return {
            "reroute_count":   reroute_count,
            "total_decisions": len(ctx.data),
            "failed_decisions": failed,
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
        graph_unavailable = False
        try:
            for _, _, edata in self._route_optimizer.graph.edges(data=True):
                if edata.get("strike_active"):
                    active_strikes = True
                    disruption_count += 1
            for _, ndata in self._route_optimizer.graph.nodes(data=True):
                if ndata.get("territory_type") == "Enemy":
                    disruption_count += 1
        except Exception as e:
            graph_unavailable = True
            logger.warning(
                f"[SituationAssessmentStage] Route graph unavailable ({e}). "
                "disruption_count forced to 1 so RoutingAgent is dispatched as a precaution. "
                "Check GeopoliticalRouteOptimizer seeding in AdaptiveOrchestrator.__init__."
            )
            # Force routing agent dispatch — better to over-dispatch than miss a live strike
            disruption_count = 1

        sigma_breach = False
        if len(delays) > 3:
            try:
                mean_d  = statistics.mean(delays)
                stdev_d = statistics.stdev(delays) or 1e-9
                sigma_breach = max(abs(d - mean_d) / stdev_d for d in delays) > 2.0
            except Exception:
                pass

        return {
            "total_records":     len(data),
            "high_risk_count":   high_risk,
            "critical_count":    critical,
            "total_exposure":    round(sum(order_values), 0),
            "active_strikes":    active_strikes,
            "disruption_count":  disruption_count,
            "sigma_breach":      sigma_breach,
            "avg_risk_score":    round(sum(risk_scores) / max(len(risk_scores), 1), 3),
            "graph_unavailable": graph_unavailable,
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
            raw  = await self._llm.execute(_DISPATCH_SYSTEM, user_msg, temperature=0.0, tenant_id=ctx.tenant_id)
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

    Execution model — three phases, purely functional (no agent mutates ctx.data):

      Phase 1 (parallel):  routing, anomaly, risk — fully independent; receive
                           an empty prior_results dict; read ctx.data read-only.
      Phase 2 (serial):    financial — reads RiskAgent result from prior_results
                           to get risk_scores; independent of routing/anomaly.
      Phase 3 (serial):    executive — synthesises all prior results for CFO brief.
      Fan-in:              row_enrichments returned by risk + financial are applied
                           to ctx.data in one pass after all agents complete.

    No agent writes directly to ctx.data rows.  All mutations go through fan-in,
    eliminating shared-state race conditions for future parallelism.

    DB sessions: agents are stateless — no SQLAlchemy sessions.  PersistenceStage
    (Stage 8) owns all DB writes after the fan-in is complete.
    """
    name = "agent_execution"

    _PHASE1_PARALLEL = frozenset({"routing", "anomaly", "risk"})
    _PHASE2_SERIAL   = ("financial",)   # ordered; needs RiskAgent prior result
    _PHASE3_LAST     = "executive"      # always runs last; synthesises everything

    def __init__(self, agents: Dict[str, Any]):
        self._agents = agents

    async def execute(self, ctx: PipelineContext) -> Dict[str, Any]:
        import asyncio as _asyncio
        import time as _time

        plan      = ctx.result("dispatch_planning").get("plan", ["risk", "financial", "executive"])
        tenant_id = ctx.tenant_id

        agent_results: Dict[str, Any] = {}
        timings:       Dict[str, float] = {}

        # ── Phase 1: parallel (routing, anomaly, risk) ────────────────────────
        phase1_names = [n for n in plan if n in self._PHASE1_PARALLEL]

        async def _run_one_parallel(agent_name: str):
            agent = self._agents.get(agent_name)
            if agent is None:
                logger.warning(f"[AgentExecutionStage] Unknown agent '{agent_name}' — skipping")
                return agent_name, None, 0.0
            t0 = _time.perf_counter()
            # Empty prior_results: phase-1 agents are fully independent
            result  = await agent.run(ctx.data, {}, tenant_id)
            elapsed = (_time.perf_counter() - t0) * 1000
            return agent_name, result, elapsed

        if phase1_names:
            p1_start   = _time.perf_counter()
            outcomes   = await _asyncio.gather(
                *[_run_one_parallel(n) for n in phase1_names],
                return_exceptions=True,
            )
            p1_elapsed = (_time.perf_counter() - p1_start) * 1000

            for outcome in outcomes:
                if isinstance(outcome, BaseException):
                    logger.error(f"[AgentExecutionStage] Phase-1 agent raised: {outcome}", exc_info=outcome)
                    continue
                agent_name, result, elapsed = outcome
                timings[agent_name] = round(elapsed, 2)
                if result is not None:
                    key = result.agent_name if hasattr(result, "agent_name") else agent_name
                    agent_results[key] = result

            logger.info(
                f"[AgentExecutionStage] Phase 1 done — {len(phase1_names)} agents "
                f"in {p1_elapsed:.1f}ms (parallel)"
            )

        # ── Phase 2: serial agents that depend on Phase 1 results ─────────────
        for agent_name in self._PHASE2_SERIAL:
            if agent_name not in plan:
                continue
            agent = self._agents.get(agent_name)
            if agent is None:
                continue
            t0 = _time.perf_counter()
            result = await agent.run(ctx.data, agent_results, tenant_id)
            timings[agent_name] = round((_time.perf_counter() - t0) * 1000, 2)
            key = result.agent_name if hasattr(result, "agent_name") else agent_name
            agent_results[key] = result

        # ── Phase 3: ExecutiveAgent (reads all prior results) ─────────────────
        if self._PHASE3_LAST in plan:
            exec_agent = self._agents.get(self._PHASE3_LAST)
            if exec_agent is not None:
                t0 = _time.perf_counter()
                result = await exec_agent.run(ctx.data, agent_results, tenant_id)
                timings[self._PHASE3_LAST] = round((_time.perf_counter() - t0) * 1000, 2)
                key = result.agent_name if hasattr(result, "agent_name") else self._PHASE3_LAST
                agent_results[key] = result

        # ── Fan-in: apply row_enrichments to ctx.data in one safe pass ────────
        self._apply_row_enrichments(ctx.data, agent_results)

        # PyTorch GNN tensors + Monte Carlo NumPy arrays are no longer needed
        # after agents complete — release before PersistenceStage allocates DB sessions
        gc.collect()

        return {
            "agent_results": agent_results,
            "agent_timings": timings,
            "agents_run":    list(timings.keys()),
        }

    @staticmethod
    def _apply_row_enrichments(
        ctx_data: list, agent_results: Dict[str, Any]
    ) -> None:
        """
        Single-pass fan-in: collect row_enrichments from all agent results and
        apply them to ctx.data rows.  Called after all three phases complete —
        no agent touches ctx.data during execution.
        """
        for result in agent_results.values():
            if not (result and getattr(result, "success", False)):
                continue
            enrichments = result.data.get("row_enrichments", [])
            for i, fields in enumerate(enrichments):
                if i < len(ctx_data):
                    ctx_data[i].update(fields)


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

        # Surface partial failures — pipeline_health.failed_stages won't catch these
        # because the stage itself succeeds; expose them explicitly.
        failed_writes = [k for k, v in results.items() if not v]
        if failed_writes:
            logger.warning(
                f"[PersistenceStage] Partial audit trail for tenant='{ctx.tenant_id}' — "
                f"failed writes: {failed_writes}. Financial results are correct; "
                f"compliance records may be incomplete."
            )
        results["partial_failure"] = bool(failed_writes)
        results["failed_writes"]   = failed_writes

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
