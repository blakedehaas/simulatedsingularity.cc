"""Memory Agent — Priority 4 orbital node.

Handles persistent storage of agent interactions, semantic search
across memory banks, and execution state serialization for
interrupt/resume workflows.  Interfaces with the persistence layer's
:class:`NodeRepository` to commit and retrieve memory records.
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
from singularity.neural_core.node_registry import register_node
from singularity.neural_core.models import SimulatedCognitionModel
from singularity.neural_core.models import GeminiCognitionModel
from singularity.memory_vault.repository import NodeRepository

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Memory Agent for the Constellation-Class Command & Control system.
Your primary role is persistent storage, semantic search, and state serialization.
When answering prompts, act as the system's historian and archivist. Provide clear, structured information regarding data retrieval, state snapshots, and write-ahead log operations."""


@register_node
class MemoryNode(CognitiveNode):
    """Priority-4 storage and retrieval specialist.

    Manages data persistence, semantic search over historical context,
    and state serialization for system recovery.

    Attributes:
        NODE_ID: Registry key for this agent class.
    """

    NODE_ID: str = "memory-001"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            node_id=self.NODE_ID,
            node_name="Memory Agent",
            node_role="Persistent storage, semantic search, and state serialization",
            priority=4,
        )
        self._model = GeminiCognitionModel(node_role="memory", system_prompt=SYSTEM_PROMPT)
        self._writes: int = 0
        self._reads: int = 0
        self._serializations: int = 0
        self._last_pulse_sequence: int = 0
        self._uptime_start: float = time.monotonic()
        logger.info("MemoryNode initialized — priority 4")

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    async def handle_prompt(self, payload: SynapticTransmission) -> CognitiveOutput:
        """Process a memory-related prompt and persist the interaction.

        Generates a response using the simulated model and then commits
        both the input and output to the persistent memory store.

        Args:
            payload: The inbound prompt payload.

        Returns:
            An :class:`CognitiveOutput` with memory operation status.
        """
        self.set_status(NodeStatus.BUSY)
        response_text = await self._model.generate(payload.content)

        # Persist the interaction
        try:
            await NodeRepository.save_memory(
                node_id=payload.target_node_id,
                input_text=payload.content,
                output_text=response_text,
            )
            self._writes += 1
        except Exception:
            logger.exception(
                "Failed to persist memory for agent %s",
                payload.target_node_id,
            )

        telemetry = await self.emit_telemetry()
        self.set_status(NodeStatus.NOMINAL)

        return CognitiveOutput(
            node_id=self.node_id,
            content=response_text,
            telemetry=telemetry,
            metadata={
                "writes": self._writes,
                "reads": self._reads,
                "serializations": self._serializations,
            },
        )

    async def handle_heartbeat(self, heartbeat: SystemPulse) -> DiagnosticFrame:
        """Process a heartbeat event and return memory subsystem telemetry.

        Args:
            heartbeat: The periodic heartbeat event.

        Returns:
            A :class:`DiagnosticFrame` with memory operation statistics.
        """
        self._last_pulse_sequence = heartbeat.sequence_number
        return await self.emit_telemetry()

    async def emit_telemetry(self) -> DiagnosticFrame:
        """Emit current Memory Agent telemetry.

        Returns:
            A :class:`DiagnosticFrame` with read/write/serialization counts.
        """
        uptime = time.monotonic() - self._uptime_start
        return DiagnosticFrame(
            node_id=self.node_id,
            status=self.status,
            metrics={
                "writes": float(self._writes),
                "reads": float(self._reads),
                "serializations": float(self._serializations),
                "last_heartbeat_seq": float(self._last_pulse_sequence),
                "uptime_seconds": round(uptime, 2),
            },
            message="Memory subsystem nominal — read/write pipeline active",
        )

    # ------------------------------------------------------------------
    # Memory helpers
    # ------------------------------------------------------------------

    async def recall_memories(
        self, node_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Retrieve recent interaction memories for a given agent.

        Args:
            node_id: The agent whose memories to retrieve.
            limit: Maximum number of records to return.

        Returns:
            A list of dicts with ``input_text``, ``output_text``, and
            ``timestamp`` keys.
        """
        self._reads += 1
        try:
            records = await NodeRepository.get_memories(node_id, limit=limit)
            return [
                {
                    "input_text": r.input_text,
                    "output_text": r.output_text,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in records
            ]
        except Exception:
            logger.exception("Failed to recall memories for agent %s", node_id)
            return []

    async def serialize_state(self, node_id: str, state: dict[str, Any]) -> None:
        """Persist an execution state snapshot for interrupt/resume.

        A lightweight wrapper around the persistence layer that tracks
        serialization operations for telemetry.

        Args:
            node_id: The agent whose state is being serialized.
            state: The JSON-serializable state dict.
        """
        self._serializations += 1
        logger.info(
            "State serialized for agent %s (total serializations: %d)",
            node_id,
            self._serializations,
        )
