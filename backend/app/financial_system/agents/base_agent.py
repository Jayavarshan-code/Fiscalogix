"""
BaseAgent — shared interface for all MAS agents.

Every agent:
  - Receives the full enriched data list and a shared results dict
    (so later agents can read what earlier ones produced)
  - Returns a typed AgentResult
  - Handles its own exceptions — a failing agent never crashes the pipeline
  - Logs timing so the adaptive orchestrator can profile bottlenecks
"""

import logging
import time
from typing import Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class AgentResult:
    agent_name: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    elapsed_ms: int = 0


class BaseAgent:
    """Abstract base — subclass and implement run_logic()."""

    name: str = "BaseAgent"

    def __init__(self):
        self.logger = logging.getLogger(f"agents.{self.name}")

    async def run(
        self,
        enriched_data: List[Dict[str, Any]],
        prior_results: Dict[str, AgentResult],
        tenant_id: str = "default_tenant",
    ) -> AgentResult:
        """
        Public entry point. Wraps run_logic() with timing and error handling.
        Never raises — always returns an AgentResult.
        """
        start = time.monotonic()
        try:
            self.logger.info(f"[{self.name}] starting on {len(enriched_data)} records")
            data = await self.run_logic(enriched_data, prior_results, tenant_id)
            elapsed = int((time.monotonic() - start) * 1000)
            self.logger.info(f"[{self.name}] completed in {elapsed}ms")
            return AgentResult(agent_name=self.name, success=True, data=data, elapsed_ms=elapsed)
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            self.logger.error(f"[{self.name}] failed — {type(e).__name__}: {e}", exc_info=True)
            return AgentResult(
                agent_name=self.name,
                success=False,
                error=f"{type(e).__name__}: {str(e)}",
                elapsed_ms=elapsed,
            )

    async def run_logic(
        self,
        enriched_data: List[Dict[str, Any]],
        prior_results: Dict[str, AgentResult],
        tenant_id: str,
    ) -> Dict[str, Any]:
        raise NotImplementedError
