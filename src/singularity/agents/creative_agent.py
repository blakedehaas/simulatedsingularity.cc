"""Creative Agent — Priority 7 orbital node.

Handles brainstorming, innovation proposals, and alternative strategy
generation.  Operates at the lowest priority in the routing chain and
is invoked when the constellation needs divergent thinking or
unconventional problem-solving approaches.
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
class CreativeAgent(AsyncBaseAgent):
    """Priority-7 ideation and creative problem-solving engine.

    Generates brainstorming output, innovation proposals, and
    alternative strategies.  Proposes novel solution pathways that
    require Core Agent approval before implementation.

    Attributes:
        AGENT_ID: Registry key for this agent class.
    """

    AGENT_ID: str = "creative-001"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            agent_id=self.AGENT_ID,
            agent_name="Creative Agent",
            agent_role="Brainstorming, innovation proposals, and alternative strategies",
            priority=7,
        )
        self._model = SimulatedChatModel(agent_role="creative")
        self._brainstorms: int = 0
        self._innovations: int = 0
        self._alternatives: int = 0
        self._last_heartbeat_seq: int = 0
        self._uptime_start: float = time.monotonic()
        logger.info("CreativeAgent initialized — priority 7")

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    async def receive_prompt(self, payload: PromptPayload) -> AgentResponse:
        """Process an ideation or creative-thinking prompt.

        Tracks the type of creative activity (brainstorm, innovation,
        alternative) and proposes an approval action when a novel
        implementation pathway is generated.

        Args:
            payload: The inbound prompt payload.

        Returns:
            An :class:`AgentResponse` with creative output.
        """
        self.set_status(AgentStatus.BUSY)

        proposed_actions: list[ProposedAction] = []
        content_lower = payload.content.lower()

        if "brainstorm" in content_lower:
            self._brainstorms += 1

        if "innovate" in content_lower or "innovation" in content_lower:
            self._innovations += 1
            action = ProposedAction(
                agent_id=self.agent_id,
                action_type="innovation_proposal",
                description="Novel solution pathway — requires Core Agent approval",
                parameters={"prompt_excerpt": payload.content[:120]},
                risk_level=RiskLevel.LOW,
            )
            proposed_actions.append(action)

        if "alternative" in content_lower:
            self._alternatives += 1

        response_text = await self._model.generate(payload.content)
        telemetry = await self.emit_telemetry()
        self.set_status(AgentStatus.NOMINAL)

        return AgentResponse(
            agent_id=self.agent_id,
            content=response_text,
            telemetry=telemetry,
            proposed_actions=proposed_actions,
            metadata={
                "brainstorms": self._brainstorms,
                "innovations": self._innovations,
                "alternatives": self._alternatives,
            },
        )

    async def process_heartbeat(self, heartbeat: HeartbeatEvent) -> TelemetryFrame:
        """Process a heartbeat and return creative subsystem telemetry.

        Args:
            heartbeat: The periodic heartbeat event.

        Returns:
            A :class:`TelemetryFrame` with ideation statistics.
        """
        self._last_heartbeat_seq = heartbeat.sequence_number
        return await self.emit_telemetry()

    async def emit_telemetry(self) -> TelemetryFrame:
        """Emit current Creative Agent telemetry.

        Returns:
            A :class:`TelemetryFrame` with brainstorm, innovation, and
            alternative counts.
        """
        uptime = time.monotonic() - self._uptime_start
        return TelemetryFrame(
            agent_id=self.agent_id,
            status=self.status,
            metrics={
                "brainstorms": float(self._brainstorms),
                "innovations": float(self._innovations),
                "alternatives": float(self._alternatives),
                "last_heartbeat_seq": float(self._last_heartbeat_seq),
                "uptime_seconds": round(uptime, 2),
            },
            message="Creative subsystem active — ready for ideation tasks",
        )
