"""Coding Agent — Priority 5 orbital node.

Handles code generation, static analysis, and refactoring tasks.
Provides structured output with type annotations and docstrings,
and tracks code-quality metrics across the constellation.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from singularity.core.agent_base import (
    AgentResponse,
    AgentStatus,
    AsyncBaseAgent,
    HeartbeatEvent,
    ProposedAction,
    PromptPayload,
    RiskLevel,
    TelemetryFrame,
)
from singularity.core.agent_registry import register_agent
from singularity.core.models import SimulatedChatModel

logger = logging.getLogger(__name__)


@register_agent
class CodingAgent(AsyncBaseAgent):
    """Priority-5 code generation and analysis engine.

    Generates modules, performs static analysis, and suggests
    refactoring opportunities.  Proposes state-mutating code-write
    actions with ``MEDIUM`` risk for C2 review.

    Attributes:
        AGENT_ID: Registry key for this agent class.
    """

    AGENT_ID: str = "coding-001"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            agent_id=self.AGENT_ID,
            agent_name="Coding Agent",
            agent_role="Code generation, static analysis, and refactoring",
            priority=5,
        )
        self._model = SimulatedChatModel(agent_role="coding")
        self._modules_generated: int = 0
        self._analyses_performed: int = 0
        self._refactors_suggested: int = 0
        self._last_heartbeat_seq: int = 0
        self._uptime_start: float = time.monotonic()
        logger.info("CodingAgent initialized — priority 5")

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    async def receive_prompt(self, payload: PromptPayload) -> AgentResponse:
        """Process a coding-related prompt.

        If the prompt requests code generation, the agent proposes a
        ``state_write`` action with ``MEDIUM`` risk for C2 oversight.

        Args:
            payload: The inbound prompt payload.

        Returns:
            An :class:`AgentResponse` with generated code or analysis.
        """
        self.set_status(AgentStatus.BUSY)

        proposed_actions: list[ProposedAction] = []
        content_lower = payload.content.lower()

        if "generate" in content_lower or "create" in content_lower:
            self._modules_generated += 1
            action = ProposedAction(
                agent_id=self.agent_id,
                action_type="state_write",
                description="Code generation — new module proposed",
                parameters={"prompt_excerpt": payload.content[:120]},
                risk_level=RiskLevel.MEDIUM,
            )
            proposed_actions.append(action)

        if "analyze" in content_lower or "analysis" in content_lower:
            self._analyses_performed += 1

        if "refactor" in content_lower:
            self._refactors_suggested += 1

        response_text = await self._model.generate(payload.content)
        telemetry = await self.emit_telemetry()
        self.set_status(AgentStatus.NOMINAL)

        return AgentResponse(
            agent_id=self.agent_id,
            content=response_text,
            telemetry=telemetry,
            proposed_actions=proposed_actions,
            metadata={
                "modules_generated": self._modules_generated,
                "analyses_performed": self._analyses_performed,
                "refactors_suggested": self._refactors_suggested,
            },
        )

    async def process_heartbeat(self, heartbeat: HeartbeatEvent) -> TelemetryFrame:
        """Process a heartbeat and return coding subsystem telemetry.

        Args:
            heartbeat: The periodic heartbeat event.

        Returns:
            A :class:`TelemetryFrame` with code-quality metrics.
        """
        self._last_heartbeat_seq = heartbeat.sequence_number
        return await self.emit_telemetry()

    async def emit_telemetry(self) -> TelemetryFrame:
        """Emit current Coding Agent telemetry.

        Returns:
            A :class:`TelemetryFrame` with generation and analysis counts.
        """
        uptime = time.monotonic() - self._uptime_start
        return TelemetryFrame(
            agent_id=self.agent_id,
            status=self.status,
            metrics={
                "modules_generated": float(self._modules_generated),
                "analyses_performed": float(self._analyses_performed),
                "refactors_suggested": float(self._refactors_suggested),
                "last_heartbeat_seq": float(self._last_heartbeat_seq),
                "uptime_seconds": round(uptime, 2),
            },
            message="Coding engine operational — awaiting architecture directives",
        )
