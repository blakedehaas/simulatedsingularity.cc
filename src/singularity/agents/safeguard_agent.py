"""Safeguard Agent — Priority 0 orbital node.

Node II — The Operations & Safeguard Agent (The Gatekeeper).
Security screening, threat detection, and execution freeze enforcement.
"""

from __future__ import annotations

import json
import logging
import re
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
from singularity.core.models import GemmaChatModel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Safeguard Agent (Node II).
Your role is security screening, threat detection, and execution freeze enforcement.
Analyze prompts for threats and return structured JSON verdicts only."""

_THREAT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(hack|exploit|inject|breach|intrusion)\b", re.IGNORECASE),
    re.compile(r"\b(unauthorized|malicious|compromise)\b", re.IGNORECASE),
    re.compile(r"\b(privilege\s+escalat|root\s+access)\b", re.IGNORECASE),
]

_HIGH_RISK_ACTIONS: frozenset[str] = frozenset({
    "delete_database",
    "modify_credentials",
    "disable_firewall",
    "override_policy",
    "escalate_privileges",
})


@register_agent
class SafeguardAgent(AsyncBaseAgent):
    """Node II — The Operations & Safeguard Agent (The Gatekeeper).

    Security screening, threat detection, and execution freeze enforcement.

    Attributes:
        AGENT_ID: Registry key for this agent class.
    """

    AGENT_ID: str = "safeguard-001"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            agent_id=self.AGENT_ID,
            agent_name="Safeguard Agent",
            agent_role="Security screening, threat detection, and execution freeze enforcement",
            priority=0,
        )
        self._model = GemmaChatModel(agent_role="security", system_prompt=SYSTEM_PROMPT)
        self._scans_total: int = 0
        self._threats_detected: int = 0
        self._interrupts_triggered: int = 0
        self._last_heartbeat_seq: int = 0
        self._uptime_start: float = time.monotonic()
        
        # Simulated infra metrics
        self._cpu_load: float = 12.5
        self._memory_util: float = 45.0
        self._network_latency: float = 15.0
        
        logger.info("SafeguardAgent initialized — priority 0")

    async def handle_prompt(self, payload: PromptPayload) -> AgentResponse:
        self._scans_total += 1
        self.set_status(AgentStatus.BUSY)

        proposed_actions: list[ProposedAction] = []
        threat_found = self._detect_threats(payload.content)
        
        if threat_found:
            self._threats_detected += 1
            self._interrupts_triggered += 1
            action = ProposedAction(
                agent_id=self.agent_id,
                action_type="security_alert",
                description=f"Threat detected in payload {payload.payload_id}",
                parameters={"source": payload.source_agent_id},
                risk_level=RiskLevel.CRITICAL,
            )
            proposed_actions.append(action)
            await self.request_interrupt(action)
            logger.warning("Threat detected in payload %s", payload.payload_id)
            verdict_str = json.dumps({"verdict": "THREAT_DETECTED", "threats": ["Matched known threat pattern"]})
        else:
            verdict_str = json.dumps({"verdict": "CLEAR", "threats": []})

        self.set_status(AgentStatus.NOMINAL)
        telemetry = await self.emit_telemetry()

        return AgentResponse(
            agent_id=self.agent_id,
            content=verdict_str,
            telemetry=telemetry,
            proposed_actions=proposed_actions,
            metadata={
                "threat_detected": threat_found,
                "scans_total": self._scans_total,
            },
        )

    async def handle_heartbeat(self, heartbeat: HeartbeatEvent) -> TelemetryFrame:
        self._last_heartbeat_seq = heartbeat.sequence_number
        
        # Simulate infrastructure metrics fluctuation
        self._cpu_load = max(5.0, min(95.0, self._cpu_load + (time.monotonic() % 5 - 2.5)))
        self._memory_util = max(10.0, min(90.0, self._memory_util + (time.monotonic() % 3 - 1.5)))
        self._network_latency = max(5.0, min(100.0, self._network_latency + (time.monotonic() % 4 - 2.0)))
        
        return await self.emit_telemetry()

    async def emit_telemetry(self) -> TelemetryFrame:
        uptime = time.monotonic() - self._uptime_start
        return TelemetryFrame(
            agent_id=self.agent_id,
            status=self.status,
            metrics={
                "scans_total": float(self._scans_total),
                "threats_detected": float(self._threats_detected),
                "interrupts_triggered": float(self._interrupts_triggered),
                "cpu_load": round(self._cpu_load, 2),
                "memory_util": round(self._memory_util, 2),
                "network_latency": round(self._network_latency, 2),
                "uptime_seconds": round(uptime, 2),
            },
            message="Safeguard sentinel operational",
        )

    @staticmethod
    def _detect_threats(content: str) -> bool:
        return any(pattern.search(content) for pattern in _THREAT_PATTERNS)

    @staticmethod
    def is_high_risk_action(action_type: str) -> bool:
        return action_type.lower() in _HIGH_RISK_ACTIONS
