"""Synthesis Agent — Priority 5 orbital node.

Node III — The Execution & Synthesis Agent (The Doer).
Stateless execution: code generation, analysis, and creative synthesis.
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
from singularity.core.models import GemmaChatModel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Synthesis Agent (Node III).
Your role fuses coding, analytical, and creative execution.
Generate code, perform deep analysis, and synthesize creative solutions based on the prompt."""


@register_agent
class SynthesisAgent(AsyncBaseAgent):
    """Node III — The Execution & Synthesis Agent (The Doer).

    Stateless execution: code generation, analysis, and creative synthesis.

    Attributes:
        AGENT_ID: Registry key for this agent class.
    """

    AGENT_ID: str = "synthesis-001"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            agent_id=self.AGENT_ID,
            agent_name="Synthesis Agent",
            agent_role="Stateless execution: code generation, analysis, and creative synthesis",
            priority=5,
        )
        self._model = GemmaChatModel(agent_role="coding", system_prompt=SYSTEM_PROMPT)
        self._tasks_executed: int = 0
        self._total_tokens_estimated: int = 0
        self._uptime_start: float = time.monotonic()
        logger.info("SynthesisAgent initialized — priority 5")

    async def receive_prompt(self, payload: PromptPayload) -> AgentResponse:
        """Override to make the agent stateless (no scratchpad logic)."""
        return await self.handle_prompt(payload)

    async def process_heartbeat(self, heartbeat: HeartbeatEvent) -> TelemetryFrame:
        """Override to skip scratchpad compaction since this agent is stateless."""
        return await self.handle_heartbeat(heartbeat)

    async def handle_prompt(self, payload: PromptPayload) -> AgentResponse:
        self._tasks_executed += 1
        self.set_status(AgentStatus.BUSY)
        
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
        
        self.set_status(AgentStatus.NOMINAL)
        telemetry = await self.emit_telemetry()

        return AgentResponse(
            agent_id=self.agent_id,
            content=response_text,
            telemetry=telemetry,
            metadata={
                "tasks_executed": self._tasks_executed,
                "task_type": task_type,
            },
        )

    async def handle_heartbeat(self, heartbeat: HeartbeatEvent) -> TelemetryFrame:
        return await self.emit_telemetry()

    async def emit_telemetry(self) -> TelemetryFrame:
        uptime = time.monotonic() - self._uptime_start
        return TelemetryFrame(
            agent_id=self.agent_id,
            status=self.status,
            metrics={
                "tasks_executed": float(self._tasks_executed),
                "total_tokens_estimated": float(self._total_tokens_estimated),
                "uptime_seconds": round(uptime, 2),
            },
            message="Synthesis execution engine operational",
        )
