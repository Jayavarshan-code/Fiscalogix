"""
PipelineContext — shared state that flows through every pipeline stage.

Design rules:
  - ctx.data is the ONLY mutable shared list; stages enrich it by stamping keys
    onto rows (e.g. predicted_delay, decision, clv_calibration).
  - ctx.stage_outputs is WRITE-ONCE per stage: the runner writes after each
    stage completes. Stages must never write here directly.
  - ctx.result(name) is the safe read accessor — always returns {}, never raises.

Mutation contract for ctx.data:
  STAMP (add a new key) = allowed by any stage
  REPLACE (overwrite an existing key) = allowed only if the stage owns that key
  DELETE = never — downstream stages may depend on the key
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StageOutput:
    """
    Immutable record of a single stage execution.
    Written by PipelineRunner; read by later stages via ctx.result().
    """
    stage:      str
    success:    bool
    data:       Dict[str, Any]
    elapsed_ms: float
    error:      Optional[str] = None


@dataclass
class PipelineContext:
    """
    Flows through every stage in the pipeline.

    Lifecycle:
      1. Created by AdaptiveOrchestrator.run() with only tenant_id set.
      2. DataIngestionStage populates ctx.data.
      3. Subsequent stages enrich ctx.data rows and/or produce
         structured outputs stored in ctx.stage_outputs.
      4. ResponseBuilderStage reads ctx.data and ctx.stage_outputs
         to assemble the final payload.
    """
    tenant_id:     str
    request_id:    str                   = field(default_factory=lambda: uuid.uuid4().hex)
    data:          List[Dict[str, Any]]  = field(default_factory=list)
    stage_outputs: Dict[str, StageOutput] = field(default_factory=dict)

    # ── Safe read accessors ───────────────────────────────────────────────────

    def result(self, stage_name: str) -> Dict[str, Any]:
        """
        Returns the data dict from a completed stage, or {} on failure/missing.
        Use this in every stage that depends on a prior stage's output —
        never access ctx.stage_outputs directly.
        """
        out = self.stage_outputs.get(stage_name)
        return out.data if (out and out.success) else {}

    def succeeded(self, stage_name: str) -> bool:
        out = self.stage_outputs.get(stage_name)
        return bool(out and out.success)

    def failed(self, stage_name: str) -> bool:
        return not self.succeeded(stage_name)

    # ── Diagnostic helpers ────────────────────────────────────────────────────

    def timing_summary(self) -> Dict[str, float]:
        """Returns {stage_name: elapsed_ms} for all completed stages."""
        return {
            name: out.elapsed_ms
            for name, out in self.stage_outputs.items()
        }

    def failed_stages(self) -> List[str]:
        return [
            name for name, out in self.stage_outputs.items()
            if not out.success
        ]

    def total_elapsed_ms(self) -> float:
        return sum(o.elapsed_ms for o in self.stage_outputs.values())
