"""Synthesis Agent — Priority 5 orbital node.

Node III — The Execution & Synthesis Agent (The Doer).
Stateless execution: code generation, analysis, and creative synthesis.
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
from singularity.neural_core.models import GeminiCognitionModel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Synthesis Agent (Node III).
Your role fuses coding, analytical, and creative execution.
Generate code, perform deep analysis, and synthesize creative solutions based on the prompt."""


@register_node
class SynthesisNode(CognitiveNode):
    """Node III — The Execution & Synthesis Agent (The Doer).

    Stateless execution: code generation, analysis, and creative synthesis.

    Attributes:
        NODE_ID: Registry key for this agent class.
    """

    NODE_ID: str = "synthesis-001"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            node_id=self.NODE_ID,
            node_name="Synthesis Agent",
            node_role="Stateless execution: code generation, analysis, and creative synthesis",
            priority=5,
        )
        self._model = GeminiCognitionModel(node_role="coding", system_prompt=SYSTEM_PROMPT)
        self._tasks_executed: int = 0
        self._total_tokens_estimated: int = 0
        self._uptime_start: float = time.monotonic()
        logger.info("SynthesisNode initialized — priority 5")

    async def receive_prompt(self, payload: SynapticTransmission) -> CognitiveOutput:
        """Override to make the agent stateless (no scratchpad logic)."""
        return await self.handle_prompt(payload)

    async def process_heartbeat(self, heartbeat: SystemPulse) -> DiagnosticFrame:
        """Override to skip scratchpad compaction since this agent is stateless."""
        return await self.handle_heartbeat(heartbeat)

    async def handle_prompt(self, payload: SynapticTransmission) -> CognitiveOutput:
        self._tasks_executed += 1
        self.set_status(NodeStatus.BUSY)
        
        content_lower = payload.content.lower()
        if any(kw in content_lower for kw in ["code", "generate", "refactor"]):
            task_type = "coding"
        elif any(kw in content_lower for kw in ["pattern", "anomaly", "metric"]):
            task_type = "analytical"
        elif any(kw in content_lower for kw in ["brainstorm", "innovate", "alternative"]):
            task_type = "creative"
        else:
            task_type = "synthesis"
            
        prompt_input = f"[Task Type: {task_type.upper()}]\\n{payload.content}"
        
        # Estimate tokens roughly
        self._total_tokens_estimated += len(prompt_input) // 4
        
        response_text = await self._model.generate(prompt_input)
        self._total_tokens_estimated += len(response_text) // 4
        
        self.set_status(NodeStatus.NOMINAL)
        telemetry = await self.emit_telemetry()

        return CognitiveOutput(
            node_id=self.node_id,
            content=response_text,
            telemetry=telemetry,
            metadata={
                "tasks_executed": self._tasks_executed,
                "task_type": task_type,
            },
        )

    async def handle_heartbeat(self, heartbeat: SystemPulse) -> DiagnosticFrame:
        return await self.emit_telemetry()

    async def emit_telemetry(self) -> DiagnosticFrame:
        uptime = time.monotonic() - self._uptime_start
        return DiagnosticFrame(
            node_id=self.node_id,
            status=self.status,
            metrics={
                "tasks_executed": float(self._tasks_executed),
                "total_tokens_estimated": float(self._total_tokens_estimated),
                "uptime_seconds": round(uptime, 2),
            },
            message="Synthesis execution engine operational",
        )
