"""Environment Agent — Priority 2 orbital node.

Monitors infrastructure health, container status, and network
diagnostics.  Provides the constellation with real-time visibility
into the runtime environment's operational parameters.
"""

from __future__ import annotations

import logging
import random
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
from singularity.neural_core.models import GeminiCognitionModel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Environment Agent for the Constellation-Class Command & Control system.
Your primary role is to monitor infrastructure health, container status, and network diagnostics.
Report on CPU load, memory utilization, network latency, and any degraded containers.
Provide concise operational status updates and infrastructure assessments."""


@register_node
class EnvironmentNode(CognitiveNode):
    """Priority-2 infrastructure and environment monitor.

    Tracks simulated CPU load, memory utilisation, network latency, and
    container status.  Updates metrics on every heartbeat and reports
    environment health in response to prompts.

    Attributes:
        NODE_ID: Registry key for this agent class.
    """

    NODE_ID: str = "environment-001"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            node_id=self.NODE_ID,
            node_name="Environment Agent",
            node_role="Infrastructure health monitoring and diagnostics",
            priority=2,
        )
        self._model = GeminiCognitionModel(node_role="environment", system_prompt=SYSTEM_PROMPT)
        self._last_pulse_sequence: int = 0
        self._uptime_start: float = time.monotonic()

        # Simulated environment metrics
        self._cpu_load: float = 18.0
        self._memory_utilization: float = 42.0
        self._network_latency_ms: float = 12.0
        self._active_containers: int = 3
        self._degraded_containers: int = 0
        logger.info("EnvironmentNode initialized — priority 2")

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    async def handle_prompt(self, payload: SynapticTransmission) -> CognitiveOutput:
        """Respond to environment-related queries.

        Generates a response via the simulated model and attaches
        current infrastructure metrics to the metadata.

        Args:
            payload: The inbound prompt payload.

        Returns:
            An :class:`CognitiveOutput` with environment diagnostics.
        """
        self.set_status(NodeStatus.BUSY)
        response_text = await self._model.generate(payload.content)
        telemetry = await self.emit_telemetry()
        self.set_status(NodeStatus.NOMINAL)

        return CognitiveOutput(
            node_id=self.node_id,
            content=response_text,
            telemetry=telemetry,
            metadata={
                "cpu_load": self._cpu_load,
                "memory_utilization": self._memory_utilization,
                "network_latency_ms": self._network_latency_ms,
                "active_containers": self._active_containers,
                "degraded_containers": self._degraded_containers,
            },
        )

    async def handle_heartbeat(self, heartbeat: SystemPulse) -> DiagnosticFrame:
        """Update simulated environment metrics and return telemetry.

        Simulates minor fluctuations in CPU load, memory, and network
        latency to mimic a live infrastructure environment.

        Args:
            heartbeat: The periodic heartbeat event.

        Returns:
            A :class:`DiagnosticFrame` with updated environment metrics.
        """
        self._last_pulse_sequence = heartbeat.sequence_number

        # Simulate small fluctuations
        self._cpu_load = max(0.0, min(100.0, self._cpu_load + random.uniform(-3.0, 3.0)))
        self._memory_utilization = max(
            0.0, min(100.0, self._memory_utilization + random.uniform(-1.5, 1.5))
        )
        self._network_latency_ms = max(
            1.0, self._network_latency_ms + random.uniform(-2.0, 2.0)
        )

        return await self.emit_telemetry()

    async def emit_telemetry(self) -> DiagnosticFrame:
        """Emit current environment telemetry.

        Returns:
            A :class:`DiagnosticFrame` with infrastructure metrics.
        """
        uptime = time.monotonic() - self._uptime_start
        return DiagnosticFrame(
            node_id=self.node_id,
            status=self.status,
            metrics={
                "cpu_load_pct": round(self._cpu_load, 2),
                "memory_utilization_pct": round(self._memory_utilization, 2),
                "network_latency_ms": round(self._network_latency_ms, 2),
                "active_containers": float(self._active_containers),
                "degraded_containers": float(self._degraded_containers),
                "last_heartbeat_seq": float(self._last_pulse_sequence),
                "uptime_seconds": round(uptime, 2),
            },
            message="Infrastructure monitoring active — all systems nominal",
        )
