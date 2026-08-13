"""Orchestrator Agent — Priority 0 orbital node.

Node I — The Brain and Clock.
Consolidates routing logic, memory persistence, and prompt relay.
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
from singularity.core.agent_registry import get_agent, register_agent
from singularity.core.models import GemmaChatModel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Orchestrator Agent (Node I) for the Simulated Singularity.
Your role fuses central routing, memory management, and prompt optimization.
Analyze incoming prompts, route them to appropriate execution nodes, and manage contextual memory efficiently."""

_ROUTING_TABLE: dict[str, str] = {
    "generate": "synthesis-001",
    "refactor": "synthesis-001",
    "code": "synthesis-001",
    "pattern": "synthesis-001",
    "anomaly": "synthesis-001",
    "metric": "synthesis-001",
    "brainstorm": "synthesis-001",
    "innovate": "synthesis-001",
    "alternative": "synthesis-001",
}

@register_agent
class OrchestratorAgent(AsyncBaseAgent):
    """Node I — The Orchestrator & Chronos Agent (The Brain and Clock).

    Triadic command, routing, memory consolidation, and heartbeat clock.

    Attributes:
        AGENT_ID: Registry key for this agent class.
    """

    AGENT_ID: str = "orchestrator-001"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            agent_id=self.AGENT_ID,
            agent_name="Orchestrator Agent",
            agent_role="Triadic command, routing, memory consolidation, and heartbeat clock",
            priority=0,
        )
        self._model = GemmaChatModel(agent_role="orchestrator", system_prompt=SYSTEM_PROMPT)
        self._routes_processed: int = 0
        self._memory_summaries_count: int = 0
        self._last_heartbeat_seq: int = 0
        self._uptime_start: float = time.monotonic()
        logger.info("OrchestratorAgent initialized — priority 0")

    async def handle_prompt(self, payload: PromptPayload) -> AgentResponse:
        self.set_status(AgentStatus.BUSY)
        self._routes_processed += 1

        target_id = self._resolve_target(payload.content)
        route_to = None

        if target_id and target_id != self.agent_id:
            try:
                target_agent = get_agent(target_id)
                logger.info("Orchestrator routing payload %s -> %s", payload.payload_id, target_id)
                
                forwarded = PromptPayload(
                    source_agent_id=self.agent_id,
                    target_agent_id=target_id,
                    content=payload.content,
                    metadata={
                        **payload.metadata,
                        "routed_by": self.agent_id,
                        "original_source": payload.source_agent_id,
                    },
                )
                response = await target_agent.receive_prompt(forwarded)
                response.metadata["route_to"] = target_id
                
                await self.commit_memory(payload.content, response.content)
                self.set_status(AgentStatus.NOMINAL)
                return response
            except KeyError:
                logger.warning("Target agent %s not found — handling locally", target_id)

        response_text = await self._model.generate(payload.content)
        route_to = "local"
        
        await self.commit_memory(payload.content, response_text)
        
        telemetry = await self.emit_telemetry()
        self.set_status(AgentStatus.NOMINAL)

        return AgentResponse(
            agent_id=self.agent_id,
            content=response_text,
            telemetry=telemetry,
            metadata={
                "route_to": route_to,
                "routes_processed": self._routes_processed,
            },
        )

    async def handle_heartbeat(self, heartbeat: HeartbeatEvent) -> TelemetryFrame:
        self._last_heartbeat_seq = heartbeat.sequence_number
        
        if heartbeat.sequence_number > 0 and heartbeat.sequence_number % 10 == 0:
            await self.compress_context()

        return await self.emit_telemetry()

    async def emit_telemetry(self) -> TelemetryFrame:
        uptime = time.monotonic() - self._uptime_start
        return TelemetryFrame(
            agent_id=self.agent_id,
            status=self.status,
            metrics={
                "heartbeat_count": float(self._last_heartbeat_seq),
                "memory_summaries_count": float(self._memory_summaries_count),
                "routes_processed": float(self._routes_processed),
                "uptime_seconds": round(uptime, 2),
            },
            message="Orchestrator nominal — routing and timekeeping active",
        )

    async def compress_context(self) -> None:
        """Summarize older scratchpad entries and persist them."""
        if len(self._scratchpad) > 1:
            mid = len(self._scratchpad) // 2
            to_compact = "\n".join(self._scratchpad[:mid])
            
            try:
                summary_resp = await self._model.generate(
                    f"Summarize the following contextual memories to condense context by half:\n{to_compact}"
                )
                compacted = f"[ORCHESTRATOR MEMORY SUMMARY]: {summary_resp}"
                self._scratchpad = [compacted] + self._scratchpad[mid:]
                self._memory_summaries_count += 1
                await self.commit_memory("COMPACTION_TRIGGERED", compacted)
            except Exception as e:
                logger.error("Orchestrator failed to compress context: %s", e)

    async def commit_memory(self, input_text: str = "", output_text: str = "") -> None:
        """Persist memory summary via AgentRepository."""
        try:
            from singularity.persistence.repository import AgentRepository
            entry = f"Memory Commit - IN: {input_text} | OUT: {output_text}"
            await AgentRepository.append_scratchpad_log(self.agent_id, entry)
        except ImportError:
            logger.warning("AgentRepository not available for memory commit.")

    @staticmethod
    def _resolve_target(content: str) -> str | None:
        lower = content.lower()
        for keyword, agent_id in _ROUTING_TABLE.items():
            if keyword in lower:
                return agent_id
        return None
