"""Core Agent — Priority 1 orbital node.

Central routing hub for the constellation.  Receives security-screened
payloads and delegates them to the appropriate functional agent based on
keyword analysis.  Manages resource allocation and task delegation across
the orbital node network.
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
    ActionProposal,
    SynapticTransmission,
    RiskLevel,
    DiagnosticFrame,
)
from singularity.neural_core.node_registry import get_node, get_all_nodes, register_node
from singularity.neural_core.models import GeminiCognitionModel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Core Agent for the Constellation-Class Command & Control system.
Your primary role is central routing, resource management, and task delegation.
When receiving a prompt, determine the most logical functional agent to handle the task and delegate it.
Provide high-level architectural insight and coordinate complex multi-agent workflows."""

# Keyword → agent-id routing table
_ROUTING_TABLE: dict[str, str] = {
    "threat": "security-001",
    "hack": "security-001",
    "audit": "security-001",
    "health": "environment-001",
    "container": "environment-001",
    "network": "environment-001",
    "broadcast": "prompt-001",
    "relay": "prompt-001",
    "heartbeat": "prompt-001",
    "store": "memory-001",
    "search": "memory-001",
    "serialize": "memory-001",
    "generate": "coding-001",
    "refactor": "coding-001",
    "code": "coding-001",
    "pattern": "analytical-001",
    "anomaly": "analytical-001",
    "metric": "analytical-001",
    "brainstorm": "creative-001",
    "innovate": "creative-001",
    "alternative": "creative-001",
}


@register_node
class NexusNode(CognitiveNode):
    """Priority-1 central router and resource manager.

    Inspects incoming prompt content for keywords and delegates to
    specialised functional agents when a match is found.  Tracks routing
    statistics and constellation health.

    Attributes:
        NODE_ID: Registry key for this agent class.
    """

    NODE_ID: str = "core-001"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            node_id=self.NODE_ID,
            node_name="Core Agent",
            node_role="Central routing, resource allocation, and task delegation",
            priority=1,
        )
        self._model = GeminiCognitionModel(node_role="core", system_prompt=SYSTEM_PROMPT)
        self._prompts_routed: int = 0
        self._delegations: int = 0
        self._last_pulse_sequence: int = 0
        self._uptime_start: float = time.monotonic()
        logger.info("NexusNode initialized — priority 1")

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    async def handle_prompt(self, payload: SynapticTransmission) -> CognitiveOutput:
        """Route an incoming prompt to the appropriate functional agent.

        Uses a keyword-based routing table to determine the best target.
        If no keyword matches, the Core Agent handles the prompt itself.

        Args:
            payload: The inbound prompt payload.

        Returns:
            An :class:`CognitiveOutput` — either from the delegated agent
            or generated locally.
        """
        self._prompts_routed += 1
        self.set_status(NodeStatus.BUSY)

        target_id = self._resolve_target(payload.content)

        if target_id and target_id != self.node_id:
            try:
                target_node = get_node(target_id)
                self._delegations += 1
                logger.info(
                    "Routing payload %s → %s",
                    payload.payload_id,
                    target_id,
                )
                # Forward payload with Core as the relay source
                forwarded = SynapticTransmission(
                    source_node_id=self.node_id,
                    target_node_id=target_id,
                    content=payload.content,
                    metadata={
                        **payload.metadata,
                        "routed_by": self.node_id,
                        "original_source": payload.source_node_id,
                    },
                )
                response = await target_node.receive_prompt(forwarded)
                self.set_status(NodeStatus.NOMINAL)
                return response
            except KeyError:
                logger.warning("Target agent %s not found — handling locally", target_id)

        # No delegation — generate local response
        response_text = await self._model.generate(payload.content)
        telemetry = await self.emit_telemetry()
        self.set_status(NodeStatus.NOMINAL)

        return CognitiveOutput(
            node_id=self.node_id,
            content=response_text,
            telemetry=telemetry,
            metadata={
                "prompts_routed": self._prompts_routed,
                "delegations": self._delegations,
            },
        )

    async def handle_heartbeat(self, heartbeat: SystemPulse) -> DiagnosticFrame:
        """Process a heartbeat and update internal constellation view.

        Args:
            heartbeat: The periodic heartbeat event.

        Returns:
            A :class:`DiagnosticFrame` with routing statistics.
        """
        self._last_pulse_sequence = heartbeat.sequence_number
        active_count = sum(
            1 for s in heartbeat.constellation_summary.values()
            if s in {NodeStatus.NOMINAL, NodeStatus.BUSY}
        )
        logger.debug(
            "Core heartbeat #%d — %d active agents",
            heartbeat.sequence_number,
            active_count,
        )
        return await self.emit_telemetry()

    async def emit_telemetry(self) -> DiagnosticFrame:
        """Emit current Core Agent telemetry.

        Returns:
            A :class:`DiagnosticFrame` with routing and delegation counts.
        """
        uptime = time.monotonic() - self._uptime_start
        return DiagnosticFrame(
            node_id=self.node_id,
            status=self.status,
            metrics={
                "prompts_routed": float(self._prompts_routed),
                "delegations": float(self._delegations),
                "last_heartbeat_seq": float(self._last_pulse_sequence),
                "uptime_seconds": round(uptime, 2),
            },
            message="Core router operational — dispatching payloads",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_target(content: str) -> str | None:
        """Scan prompt content and return the best-match agent ID.

        Args:
            content: The prompt text to analyse.

        Returns:
            An agent ID string if a keyword matches, otherwise ``None``.
        """
        lower = content.lower()
        for keyword, node_id in _ROUTING_TABLE.items():
            if keyword in lower:
                return node_id
        return None
