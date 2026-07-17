"""Prompt Agent — Priority 3 orbital node.

Communications relay responsible for message routing, telemetry
aggregation, and heartbeat distribution across the constellation.
Acts as the primary comms backbone between Ground Control, the
scheduler, and all functional agents.
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
    PromptPayload,
    TelemetryFrame,
)
from singularity.core.agent_registry import get_all_agents, register_agent
from singularity.core.models import SimulatedChatModel

logger = logging.getLogger(__name__)


@register_agent
class PromptAgent(AsyncBaseAgent):
    """Priority-3 communications relay and telemetry aggregator.

    Handles message relay between agents, aggregates telemetry frames,
    and distributes heartbeat events to the constellation.

    Attributes:
        AGENT_ID: Registry key for this agent class.
    """

    AGENT_ID: str = "prompt-001"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            agent_id=self.AGENT_ID,
            agent_name="Prompt Agent",
            agent_role="Message relay, telemetry aggregation, and heartbeat distribution",
            priority=3,
        )
        self._model = SimulatedChatModel(agent_role="prompt")
        self._messages_relayed: int = 0
        self._broadcasts_sent: int = 0
        self._last_heartbeat_seq: int = 0
        self._uptime_start: float = time.monotonic()
        self._telemetry_cache: dict[str, TelemetryFrame] = {}
        logger.info("PromptAgent initialized — priority 3")

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    async def receive_prompt(self, payload: PromptPayload) -> AgentResponse:
        """Process a communications-related prompt.

        Handles relay, broadcast, and heartbeat-related queries.
        Tracks message relay statistics for telemetry.

        Args:
            payload: The inbound prompt payload.

        Returns:
            An :class:`AgentResponse` with relay status.
        """
        self._messages_relayed += 1
        self.set_status(AgentStatus.BUSY)

        response_text = await self._model.generate(payload.content)
        telemetry = await self.emit_telemetry()
        self.set_status(AgentStatus.NOMINAL)

        return AgentResponse(
            agent_id=self.agent_id,
            content=response_text,
            telemetry=telemetry,
            metadata={
                "messages_relayed": self._messages_relayed,
                "broadcasts_sent": self._broadcasts_sent,
                "cached_telemetry_agents": list(self._telemetry_cache.keys()),
            },
        )

    async def process_heartbeat(self, heartbeat: HeartbeatEvent) -> TelemetryFrame:
        """Process a heartbeat and update relay metrics.

        Caches the constellation status from the heartbeat and updates
        the broadcast counter.

        Args:
            heartbeat: The periodic heartbeat event.

        Returns:
            A :class:`TelemetryFrame` with relay statistics.
        """
        self._last_heartbeat_seq = heartbeat.sequence_number
        self._broadcasts_sent += 1

        logger.debug(
            "Prompt relay heartbeat #%d — %d agents in constellation",
            heartbeat.sequence_number,
            len(heartbeat.constellation_summary),
        )
        return await self.emit_telemetry()

    async def emit_telemetry(self) -> TelemetryFrame:
        """Emit current Prompt Agent telemetry.

        Returns:
            A :class:`TelemetryFrame` with relay and broadcast counts.
        """
        uptime = time.monotonic() - self._uptime_start
        return TelemetryFrame(
            agent_id=self.agent_id,
            status=self.status,
            metrics={
                "messages_relayed": float(self._messages_relayed),
                "broadcasts_sent": float(self._broadcasts_sent),
                "last_heartbeat_seq": float(self._last_heartbeat_seq),
                "telemetry_cache_size": float(len(self._telemetry_cache)),
                "uptime_seconds": round(uptime, 2),
            },
            message="Comms relay operational — message pipeline active",
        )

    # ------------------------------------------------------------------
    # Relay helpers
    # ------------------------------------------------------------------

    async def broadcast_to_all(self, payload: PromptPayload) -> list[AgentResponse]:
        """Broadcast a prompt payload to every active agent.

        Args:
            payload: The payload to broadcast.

        Returns:
            A list of :class:`AgentResponse` from each agent that
            successfully processed the broadcast.
        """
        agents = get_all_agents()
        responses: list[AgentResponse] = []

        for agent in agents:
            if agent.agent_id == self.agent_id:
                continue
            try:
                forwarded = PromptPayload(
                    source_agent_id=self.agent_id,
                    target_agent_id=agent.agent_id,
                    content=payload.content,
                    metadata={
                        **payload.metadata,
                        "broadcast": True,
                        "relay_agent": self.agent_id,
                    },
                )
                response = await agent.receive_prompt(forwarded)
                responses.append(response)
            except Exception:
                logger.exception(
                    "Failed to relay broadcast to agent %s", agent.agent_id
                )

        self._broadcasts_sent += 1
        logger.info(
            "Broadcast complete — %d/%d agents responded",
            len(responses),
            len(agents) - 1,
        )
        return responses

    def cache_telemetry(self, frame: TelemetryFrame) -> None:
        """Cache a telemetry frame from another agent.

        Args:
            frame: The telemetry frame to cache.
        """
        self._telemetry_cache[frame.agent_id] = frame

    def get_cached_telemetry(self, agent_id: str) -> TelemetryFrame | None:
        """Retrieve a cached telemetry frame for a given agent.

        Args:
            agent_id: The agent whose telemetry to look up.

        Returns:
            The cached :class:`TelemetryFrame`, or ``None`` if not found.
        """
        return self._telemetry_cache.get(agent_id)
