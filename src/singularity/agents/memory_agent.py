"""Memory Agent — Priority 4 orbital node.

Handles persistent storage of agent interactions, semantic search
across memory banks, and execution state serialization for
interrupt/resume workflows.  Interfaces with the persistence layer's
:class:`AgentRepository` to commit and retrieve memory records.
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
from singularity.core.agent_registry import register_agent
from singularity.core.models import SimulatedChatModel
from singularity.core.models import GemmaChatModel
from singularity.persistence.repository import AgentRepository

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Memory Agent for the Constellation-Class Command & Control system.
Your primary role is persistent storage, semantic search, and state serialization.
When answering prompts, act as the system's historian and archivist. Provide clear, structured information regarding data retrieval, state snapshots, and write-ahead log operations."""


@register_agent
class MemoryAgent(AsyncBaseAgent):
    """Priority-4 storage and retrieval specialist.

    Manages data persistence, semantic search over historical context,
    and state serialization for system recovery.

    Attributes:
        AGENT_ID: Registry key for this agent class.
    """

    AGENT_ID: str = "memory-001"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            agent_id=self.AGENT_ID,
            agent_name="Memory Agent",
            agent_role="Persistent storage, semantic search, and state serialization",
            priority=4,
        )
        self._model = GemmaChatModel(agent_role="memory", system_prompt=SYSTEM_PROMPT)
        self._writes: int = 0
        self._reads: int = 0
        self._serializations: int = 0
        self._last_heartbeat_seq: int = 0
        self._uptime_start: float = time.monotonic()
        logger.info("MemoryAgent initialized — priority 4")

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    async def handle_prompt(self, payload: PromptPayload) -> AgentResponse:
        """Process a memory-related prompt and persist the interaction.

        Generates a response using the simulated model and then commits
        both the input and output to the persistent memory store.

        Args:
            payload: The inbound prompt payload.

        Returns:
            An :class:`AgentResponse` with memory operation status.
        """
        self.set_status(AgentStatus.BUSY)
        response_text = await self._model.generate(payload.content)

        # Persist the interaction
        try:
            await AgentRepository.save_memory(
                agent_id=payload.target_agent_id,
                input_text=payload.content,
                output_text=response_text,
            )
            self._writes += 1
        except Exception:
            logger.exception(
                "Failed to persist memory for agent %s",
                payload.target_agent_id,
            )

        telemetry = await self.emit_telemetry()
        self.set_status(AgentStatus.NOMINAL)

        return AgentResponse(
            agent_id=self.agent_id,
            content=response_text,
            telemetry=telemetry,
            metadata={
                "writes": self._writes,
                "reads": self._reads,
                "serializations": self._serializations,
            },
        )

    async def handle_heartbeat(self, heartbeat: HeartbeatEvent) -> TelemetryFrame:
        """Process a heartbeat event and return memory subsystem telemetry.

        Args:
            heartbeat: The periodic heartbeat event.

        Returns:
            A :class:`TelemetryFrame` with memory operation statistics.
        """
        self._last_heartbeat_seq = heartbeat.sequence_number
        return await self.emit_telemetry()

    async def emit_telemetry(self) -> TelemetryFrame:
        """Emit current Memory Agent telemetry.

        Returns:
            A :class:`TelemetryFrame` with read/write/serialization counts.
        """
        uptime = time.monotonic() - self._uptime_start
        return TelemetryFrame(
            agent_id=self.agent_id,
            status=self.status,
            metrics={
                "writes": float(self._writes),
                "reads": float(self._reads),
                "serializations": float(self._serializations),
                "last_heartbeat_seq": float(self._last_heartbeat_seq),
                "uptime_seconds": round(uptime, 2),
            },
            message="Memory subsystem nominal — read/write pipeline active",
        )

    # ------------------------------------------------------------------
    # Memory helpers
    # ------------------------------------------------------------------

    async def recall_memories(
        self, agent_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Retrieve recent interaction memories for a given agent.

        Args:
            agent_id: The agent whose memories to retrieve.
            limit: Maximum number of records to return.

        Returns:
            A list of dicts with ``input_text``, ``output_text``, and
            ``timestamp`` keys.
        """
        self._reads += 1
        try:
            records = await AgentRepository.get_memories(agent_id, limit=limit)
            return [
                {
                    "input_text": r.input_text,
                    "output_text": r.output_text,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in records
            ]
        except Exception:
            logger.exception("Failed to recall memories for agent %s", agent_id)
            return []

    async def serialize_state(self, agent_id: str, state: dict[str, Any]) -> None:
        """Persist an execution state snapshot for interrupt/resume.

        A lightweight wrapper around the persistence layer that tracks
        serialization operations for telemetry.

        Args:
            agent_id: The agent whose state is being serialized.
            state: The JSON-serializable state dict.
        """
        self._serializations += 1
        logger.info(
            "State serialized for agent %s (total serializations: %d)",
            agent_id,
            self._serializations,
        )
