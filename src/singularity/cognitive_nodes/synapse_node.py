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

from singularity.neural_core.node_base import (
    CognitiveOutput,
    NodeStatus,
    CognitiveNode,
    SystemPulse,
    SynapticTransmission,
    DiagnosticFrame,
)
from singularity.neural_core.node_registry import get_all_nodes, register_node
from singularity.neural_core.models import GeminiCognitionModel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Prompt Agent for the Constellation-Class Command & Control system.
Your primary role is acting as a communications relay, aggregating telemetry, and routing heartbeat events.
When interacting with the user, maintain the persona of a reliable comms backbone,
formatting output cleanly and summarizing relayed messages when requested."""


@register_node
class SynapseNode(CognitiveNode):
    """Priority-3 communications relay and telemetry aggregator.

    Handles message relay between agents, aggregates telemetry frames,
    and distributes heartbeat events to the constellation.

    Attributes:
        NODE_ID: Registry key for this agent class.
    """

    NODE_ID: str = "prompt-001"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            node_id=self.NODE_ID,
            node_name="Prompt Agent",
            node_role="Message relay, telemetry aggregation, and heartbeat distribution",
            priority=3,
        )
        self._model = GeminiCognitionModel(node_role="prompt", system_prompt=SYSTEM_PROMPT)
        self._messages_relayed: int = 0
        self._broadcasts_sent: int = 0
        self._last_pulse_sequence: int = 0
        self._uptime_start: float = time.monotonic()
        self._diagnostics_cache: dict[str, DiagnosticFrame] = {}
        logger.info("SynapseNode initialized — priority 3")

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    async def handle_prompt(self, payload: SynapticTransmission) -> CognitiveOutput:
        """Process a communications-related prompt.

        Handles relay, broadcast, and heartbeat-related queries.
        Tracks message relay statistics for telemetry.

        Args:
            payload: The inbound prompt payload.

        Returns:
            An :class:`CognitiveOutput` with relay status.
        """
        self._messages_relayed += 1
        self.set_status(NodeStatus.BUSY)

        response_text = await self._model.generate(payload.content)
        telemetry = await self.emit_telemetry()
        self.set_status(NodeStatus.NOMINAL)

        return CognitiveOutput(
            node_id=self.node_id,
            content=response_text,
            telemetry=telemetry,
            metadata={
                "messages_relayed": self._messages_relayed,
                "broadcasts_sent": self._broadcasts_sent,
                "cached_telemetry_agents": list(self._diagnostics_cache.keys()),
            },
        )

    async def handle_heartbeat(self, heartbeat: SystemPulse) -> DiagnosticFrame:
        """Process a heartbeat and update relay metrics.

        Caches the constellation status from the heartbeat and updates
        the broadcast counter.

        Args:
            heartbeat: The periodic heartbeat event.

        Returns:
            A :class:`DiagnosticFrame` with relay statistics.
        """
        self._last_pulse_sequence = heartbeat.sequence_number
        self._broadcasts_sent += 1

        logger.debug(
            "Prompt relay heartbeat #%d — %d agents in constellation",
            heartbeat.sequence_number,
            len(heartbeat.constellation_summary),
        )
        return await self.emit_telemetry()

    async def emit_telemetry(self) -> DiagnosticFrame:
        """Emit current Prompt Agent telemetry.

        Returns:
            A :class:`DiagnosticFrame` with relay and broadcast counts.
        """
        uptime = time.monotonic() - self._uptime_start
        return DiagnosticFrame(
            node_id=self.node_id,
            status=self.status,
            metrics={
                "messages_relayed": float(self._messages_relayed),
                "broadcasts_sent": float(self._broadcasts_sent),
                "last_heartbeat_seq": float(self._last_pulse_sequence),
                "telemetry_cache_size": float(len(self._diagnostics_cache)),
                "uptime_seconds": round(uptime, 2),
            },
            message="Comms relay operational — message pipeline active",
        )

    # ------------------------------------------------------------------
    # Relay helpers
    # ------------------------------------------------------------------

    async def broadcast_to_all(self, payload: SynapticTransmission) -> list[CognitiveOutput]:
        """Broadcast a prompt payload to every active agent.

        Args:
            payload: The payload to broadcast.

        Returns:
            A list of :class:`CognitiveOutput` from each agent that
            successfully processed the broadcast.
        """
        agents = get_all_nodes()
        responses: list[CognitiveOutput] = []

        for agent in agents:
            if agent.node_id == self.node_id:
                continue
            try:
                forwarded = SynapticTransmission(
                    source_node_id=self.node_id,
                    target_node_id=agent.node_id,
                    content=payload.content,
                    metadata={
                        **payload.metadata,
                        "broadcast": True,
                        "relay_agent": self.node_id,
                    },
                )
                response = await agent.receive_prompt(forwarded)
                responses.append(response)
            except Exception:
                logger.exception(
                    "Failed to relay broadcast to agent %s", agent.node_id
                )

        self._broadcasts_sent += 1
        logger.info(
            "Broadcast complete — %d/%d agents responded",
            len(responses),
            len(agents) - 1,
        )
        return responses

    def cache_diagnostics(self, frame: DiagnosticFrame) -> None:
        """Cache a telemetry frame from another agent.

        Args:
            frame: The telemetry frame to cache.
        """
        self._diagnostics_cache[frame.node_id] = frame

    def get_cached_diagnostics(self, node_id: str) -> DiagnosticFrame | None:
        """Retrieve a cached telemetry frame for a given agent.

        Args:
            node_id: The agent whose telemetry to look up.

        Returns:
            The cached :class:`DiagnosticFrame`, or ``None`` if not found.
        """
        return self._diagnostics_cache.get(node_id)
