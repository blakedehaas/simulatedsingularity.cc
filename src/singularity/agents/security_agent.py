"""Security Agent — Priority 0 orbital node.

Responsible for threat detection, policy enforcement, access-control
validation, and interrupt escalation for high-risk proposed actions.
Sits at the top of the routing priority chain so that every inbound
payload is security-screened before reaching functional agents.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from singularity.core.agent_base import (
    AgentResponse,
    AgentStatus,
    HeartbeatEvent,
    ProposedAction,
    PromptPayload,
    RiskLevel,
    TelemetryFrame,
)
from singularity.core.agent_registry import register_agent
from singularity.core.models import SimulatedChatModel

logger = logging.getLogger(__name__)

# Patterns that indicate a potential threat in incoming content
_THREAT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(hack|exploit|inject|breach|intrusion)\b", re.IGNORECASE),
    re.compile(r"\b(unauthorized|malicious|compromise)\b", re.IGNORECASE),
    re.compile(r"\b(privilege\s+escalat|root\s+access)\b", re.IGNORECASE),
]

# Keywords that indicate a high-risk action
_HIGH_RISK_ACTIONS: frozenset[str] = frozenset({
    "delete_database",
    "modify_credentials",
    "disable_firewall",
    "override_policy",
    "escalate_privileges",
})


from singularity.core.agent_base import AsyncBaseAgent

@register_agent
class SecurityAgent(AsyncBaseAgent):
    """Priority-0 sentinel that screens all inbound payloads.

    Detects threat patterns in prompt content and triggers
    :class:`InterruptRequest` objects for high-risk proposed actions,
    ensuring C2 approval before execution proceeds.

    Attributes:
        AGENT_ID: Registry key for this agent class.
    """

    AGENT_ID: str = "security-001"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            agent_id=self.AGENT_ID,
            agent_name="Security Agent",
            agent_role="Threat detection, policy enforcement, and access-control sentinel",
            priority=0,
        )
        self._model = SimulatedChatModel(agent_role="security")
        self._threats_detected: int = 0
        self._payloads_screened: int = 0
        self._last_heartbeat_seq: int = 0
        self._uptime_start: float = time.monotonic()
        logger.info("SecurityAgent initialized — priority 0")

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    async def receive_prompt(self, payload: PromptPayload) -> AgentResponse:
        """Screen an incoming prompt for threats and generate a response.

        If threat patterns are detected the agent creates a
        :class:`ProposedAction` with ``CRITICAL`` risk and triggers an
        interrupt request.

        Args:
            payload: The inbound prompt payload.

        Returns:
            An :class:`AgentResponse` containing the screening verdict.
        """
        self._payloads_screened += 1
        self.set_status(AgentStatus.BUSY)

        proposed_actions: list[ProposedAction] = []
        threat_found = self._detect_threats(payload.content)

        if threat_found:
            self._threats_detected += 1
            action = ProposedAction(
                agent_id=self.agent_id,
                action_type="security_alert",
                description=f"Threat detected in payload {payload.payload_id}",
                parameters={"source": payload.source_agent_id},
                risk_level=RiskLevel.CRITICAL,
            )
            proposed_actions.append(action)
            await self.request_interrupt(action)
            logger.warning(
                "Threat detected in payload %s from %s",
                payload.payload_id,
                payload.source_agent_id,
            )

        response_text = await self._model.generate(payload.content)
        telemetry = await self.emit_telemetry()
        self.set_status(AgentStatus.NOMINAL)

        return AgentResponse(
            agent_id=self.agent_id,
            content=response_text,
            telemetry=telemetry,
            proposed_actions=proposed_actions,
            metadata={
                "threat_detected": threat_found,
                "payloads_screened": self._payloads_screened,
            },
        )

    async def process_heartbeat(self, heartbeat: HeartbeatEvent) -> TelemetryFrame:
        """Process a heartbeat event and return current telemetry.

        Updates internal counters and verifies that the constellation
        summary does not contain agents in an ``ERROR`` state.

        Args:
            heartbeat: The periodic heartbeat event.

        Returns:
            A :class:`TelemetryFrame` with security-specific metrics.
        """
        self._last_heartbeat_seq = heartbeat.sequence_number

        # Flag agents in ERROR state as a security concern
        error_agents = [
            aid for aid, status in heartbeat.constellation_summary.items()
            if status == AgentStatus.ERROR
        ]
        if error_agents:
            logger.warning(
                "Security concern: agents in ERROR state — %s",
                ", ".join(error_agents),
            )

        return await self.emit_telemetry()

    async def emit_telemetry(self) -> TelemetryFrame:
        """Emit current security telemetry metrics.

        Returns:
            A :class:`TelemetryFrame` snapshot with threat-detection
            statistics and uptime data.
        """
        uptime = time.monotonic() - self._uptime_start
        return TelemetryFrame(
            agent_id=self.agent_id,
            status=self.status,
            metrics={
                "threats_detected": float(self._threats_detected),
                "payloads_screened": float(self._payloads_screened),
                "last_heartbeat_seq": float(self._last_heartbeat_seq),
                "uptime_seconds": round(uptime, 2),
            },
            message="Security sentinel active — scanning all payloads",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_threats(content: str) -> bool:
        """Check prompt content against known threat patterns.

        Args:
            content: The text to scan.

        Returns:
            ``True`` if any threat pattern matches.
        """
        return any(pattern.search(content) for pattern in _THREAT_PATTERNS)

    @staticmethod
    def is_high_risk_action(action_type: str) -> bool:
        """Determine whether an action type is classified as high-risk.

        Args:
            action_type: The action type string to evaluate.

        Returns:
            ``True`` if the action is in the high-risk set.
        """
        return action_type.lower() in _HIGH_RISK_ACTIONS



