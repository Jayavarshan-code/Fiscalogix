"""
PipelineRunner — executes stages in sequence with per-stage failure isolation.

Key guarantee:
  No stage failure propagates to subsequent stages. Every stage gets a
  fully-formed PipelineContext regardless of what happened before it.
  The pipeline ALWAYS completes — it never raises.

Observability:
  Every stage execution is timed and recorded as a StageOutput in ctx.stage_outputs.
  Failed stages log at ERROR level with full traceback.
  The final ctx.timing_summary() and ctx.failed_stages() give ops full visibility.

Usage:
    runner = PipelineRunner(stages=[
        DataIngestionStage(core),
        MLInferenceStage(delay_model, demand_model),
        ...
    ])
    ctx = await runner.execute(PipelineContext(tenant_id="acme"))
    # ctx.data is fully enriched; ctx.stage_outputs has every stage's result
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from typing import List

from app.financial_system.pipeline.context import PipelineContext, StageOutput
from app.financial_system.pipeline.stages import PipelineStage

logger = logging.getLogger(__name__)


class PipelineRunner:
    """
    Runs a list of PipelineStages in order.

    - Both sync and async stage.execute() methods are supported.
    - Failure in any stage is caught, logged, and recorded as a failed StageOutput.
    - The remaining stages always execute.
    """

    def __init__(self, stages: List[PipelineStage]):
        if not stages:
            raise ValueError("PipelineRunner requires at least one stage.")
        self._stages = stages

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        """
        Execute all stages in order, accumulating results into ctx.
        Always returns the context — never raises.
        """
        total_stages = len(self._stages)
        logger.info(
            f"[Pipeline] Starting {total_stages}-stage pipeline for tenant='{ctx.tenant_id}'"
        )

        for i, stage in enumerate(self._stages, start=1):
            stage_label = f"[{i}/{total_stages}] {stage.name}"
            t0 = time.perf_counter()

            try:
                # Support both sync and async execute() transparently
                if inspect.iscoroutinefunction(stage.execute):
                    output_data = await stage.execute(ctx)
                else:
                    output_data = stage.execute(ctx)

                elapsed = (time.perf_counter() - t0) * 1000
                ctx.stage_outputs[stage.name] = StageOutput(
                    stage=stage.name,
                    success=True,
                    data=output_data or {},
                    elapsed_ms=round(elapsed, 2),
                )
                logger.info(f"[Pipeline] {stage_label} ✓  {elapsed:.1f}ms")

            except Exception as exc:
                elapsed = (time.perf_counter() - t0) * 1000
                ctx.stage_outputs[stage.name] = StageOutput(
                    stage=stage.name,
                    success=False,
                    data={},
                    elapsed_ms=round(elapsed, 2),
                    error=str(exc),
                )
                # Full traceback at ERROR level — never swallowed silently
                logger.error(
                    f"[Pipeline] {stage_label} ✗  {elapsed:.1f}ms — {exc}",
                    exc_info=True,
                )
                # Pipeline continues — next stage runs with ctx.result(stage.name) == {}

        failed = ctx.failed_stages()
        if failed:
            logger.warning(
                f"[Pipeline] Completed with {len(failed)} failed stage(s): {failed}  "
                f"total={ctx.total_elapsed_ms():.0f}ms"
            )
        else:
            logger.info(
                f"[Pipeline] All stages succeeded  total={ctx.total_elapsed_ms():.0f}ms  "
                f"breakdown={ctx.timing_summary()}"
            )

        return ctx
