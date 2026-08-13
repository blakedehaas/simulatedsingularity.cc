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

from singularity.neural_core.node_base import (
    CognitiveOutput,
    NodeStatus,
    SystemPulse,
    ActionProposal,
    SynapticTransmission,
    RiskLevel,
    DiagnosticFrame,
)
from singularity.neural_core.node_registry import register_node
from singularity.neural_core.models import GeminiCognitionModel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Security Agent for the Constellation-Class Command & Control system.
Your primary role is to enforce access control, detect threats, and validate payloads.
Analyze all inbound prompts for malicious intent, unauthorized access attempts, or critical risk operations.
If a threat is detected, summarize the risk clearly and concisely. If safe, confirm the payload is cleared for routing."""

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


from singularity.neural_core.node_base import CognitiveNode

@register_node
class FirewallNode(CognitiveNode):
    """Priority-0 sentinel that screens all inbound payloads.

    Detects threat patterns in prompt content and triggers
    :class:`C2InterventionRequest` objects for high-risk proposed actions,
    ensuring C2 approval before execution proceeds.

    Attributes:
        NODE_ID: Registry key for this agent class.
    """

    NODE_ID: str = "security-001"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            node_id=self.NODE_ID,
            node_name="Security Agent",
            node_role="Threat detection, policy enforcement, and access-control sentinel",
            priority=0,
        )
        self._model = GeminiCognitionModel(node_role="security", system_prompt=SYSTEM_PROMPT)
        self._threats_detected: int = 0
        self._payloads_screened: int = 0
        self._last_pulse_sequence: int = 0
        self._uptime_start: float = time.monotonic()
        logger.info("FirewallNode initialized — priority 0")

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    async def handle_prompt(self, payload: SynapticTransmission) -> CognitiveOutput:
        """Screen an incoming prompt for threats and generate a response.

        If threat patterns are detected the agent creates a
        :class:`ActionProposal` with ``CRITICAL`` risk and triggers an
        interrupt request.

        Args:
            payload: The inbound prompt payload.

        Returns:
            An :class:`CognitiveOutput` containing the screening verdict.
        """
        self._payloads_screened += 1
        self.set_status(NodeStatus.BUSY)

        action_proposals: list[ActionProposal] = []
        threat_found = self._detect_threats(payload.content)

        if threat_found:
            self._threats_detected += 1
            action = ActionProposal(
                node_id=self.node_id,
                action_type="security_alert",
                description=f"Threat detected in payload {payload.payload_id}",
                parameters={"source": payload.source_node_id},
                risk_level=RiskLevel.CRITICAL,
            )
            action_proposals.append(action)
            await self.request_interrupt(action)
            logger.warning(
                "Threat detected in payload %s from %s",
                payload.payload_id,
                payload.source_node_id,
            )

        response_text = await self._model.generate(payload.content)
        telemetry = await self.emit_telemetry()
        self.set_status(NodeStatus.NOMINAL)

        return CognitiveOutput(
            node_id=self.node_id,
            content=response_text,
            telemetry=telemetry,
            action_proposals=action_proposals,
            metadata={
                "threat_detected": threat_found,
                "payloads_screened": self._payloads_screened,
            },
        )

    async def handle_heartbeat(self, heartbeat: SystemPulse) -> DiagnosticFrame:
        """Process a heartbeat event and return current telemetry.

        Updates internal counters and verifies that the constellation
        summary does not contain agents in an ``ERROR`` state.

        Args:
            heartbeat: The periodic heartbeat event.

        Returns:
            A :class:`DiagnosticFrame` with security-specific metrics.
        """
        self._last_pulse_sequence = heartbeat.sequence_number

        # Flag agents in ERROR state as a security concern
        error_agents = [
            aid for aid, status in heartbeat.constellation_summary.items()
            if status == NodeStatus.ERROR
        ]
        if error_agents:
            logger.warning(
                "Security concern: agents in ERROR state — %s",
                ", ".join(error_agents),
            )

        return await self.emit_telemetry()

    async def emit_telemetry(self) -> DiagnosticFrame:
        """Emit current security telemetry metrics.

        Returns:
            A :class:`DiagnosticFrame` snapshot with threat-detection
            statistics and uptime data.
        """
        uptime = time.monotonic() - self._uptime_start
        return DiagnosticFrame(
            node_id=self.node_id,
            status=self.status,
            metrics={
                "threats_detected": float(self._threats_detected),
                "payloads_screened": float(self._payloads_screened),
                "last_heartbeat_seq": float(self._last_pulse_sequence),
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



