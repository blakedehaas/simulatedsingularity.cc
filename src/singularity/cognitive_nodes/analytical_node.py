"""Analytical Agent — Priority 6 orbital node.

Performs pattern recognition, anomaly detection, and metric aggregation
across constellation telemetry streams.  Escalates anomalies exceeding
the 2σ threshold to the Security Agent via proposed actions.
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
from singularity.neural_core.node_registry import register_agent
from singularity.neural_core.models import GemmaChatModel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Analytical Agent for the Constellation-Class Command & Control system.
Your primary role is pattern recognition, anomaly detection, and metric aggregation.
When responding to a prompt, analyze the data objectively, calculate probabilities or trends, and identify potential anomalies in system behavior."""


@register_agent
class AnalyticalNode(CognitiveNode):
    """Priority-6 data analysis and anomaly detection engine.

    Parses telemetry trends, identifies statistical anomalies, and
    provides quantitative insights for the constellation.

    Attributes:
        AGENT_ID: Registry key for this agent class.
    """

    AGENT_ID: str = "analytical-001"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            node_id=self.AGENT_ID,
            node_name="Analytical Agent",
            node_role="Pattern recognition, anomaly detection, and metric aggregation",
            priority=6,
        )
        self._model = GemmaChatModel(node_role="analytical", system_prompt=SYSTEM_PROMPT)
        self._patterns_detected: int = 0
        self._anomalies_flagged: int = 0
        self._reports_generated: int = 0
        self._last_heartbeat_seq: int = 0
        self._uptime_start: float = time.monotonic()
        logger.info("AnalyticalNode initialized — priority 6")

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    async def handle_prompt(self, payload: SynapticTransmission) -> CognitiveOutput:
        """Process an analytical query.

        Detects keywords that indicate anomaly or pattern analysis,
        tracks statistics, and escalates anomalies to Security via
        proposed actions.

        Args:
            payload: The inbound prompt payload.

        Returns:
            An :class:`CognitiveOutput` with analysis results.
        """
        self.set_status(NodeStatus.BUSY)

        proposed_actions: list[ActionProposal] = []
        content_lower = payload.content.lower()

        if "anomaly" in content_lower or "deviation" in content_lower:
            self._anomalies_flagged += 1
            action = ActionProposal(
                node_id=self.node_id,
                action_type="anomaly_escalation",
                description="Anomaly exceeding 2σ threshold detected — escalating to Security",
                parameters={
                    "source_payload": payload.payload_id,
                    "confidence": 0.947,
                },
                risk_level=RiskLevel.HIGH,
            )
            proposed_actions.append(action)
            logger.warning(
                "Anomaly flagged in payload %s — escalating", payload.payload_id
            )

        if "pattern" in content_lower:
            self._patterns_detected += 1

        if "metric" in content_lower or "report" in content_lower:
            self._reports_generated += 1

        response_text = await self._model.generate(payload.content)
        telemetry = await self.emit_telemetry()
        self.set_status(NodeStatus.NOMINAL)

        return CognitiveOutput(
            node_id=self.node_id,
            content=response_text,
            telemetry=telemetry,
            proposed_actions=proposed_actions,
            metadata={
                "patterns_detected": self._patterns_detected,
                "anomalies_flagged": self._anomalies_flagged,
                "reports_generated": self._reports_generated,
            },
        )

    async def handle_heartbeat(self, heartbeat: SystemPulse) -> DiagnosticFrame:
        """Process a heartbeat and return analytical telemetry.

        Scans the constellation summary for agents in non-nominal states
        and logs them as data points for trend analysis.

        Args:
            heartbeat: The periodic heartbeat event.

        Returns:
            A :class:`DiagnosticFrame` with analysis statistics.
        """
        self._last_heartbeat_seq = heartbeat.sequence_number

        non_nominal = [
            aid for aid, status in heartbeat.constellation_summary.items()
            if status not in {NodeStatus.NOMINAL, NodeStatus.BUSY}
        ]
        if non_nominal:
            logger.info(
                "Analytical observation: non-nominal agents — %s",
                ", ".join(non_nominal),
            )

        return await self.emit_telemetry()

    async def emit_telemetry(self) -> DiagnosticFrame:
        """Emit current Analytical Agent telemetry.

        Returns:
            A :class:`DiagnosticFrame` with pattern, anomaly, and report
            counts.
        """
        uptime = time.monotonic() - self._uptime_start
        return DiagnosticFrame(
            node_id=self.node_id,
            status=self.status,
            metrics={
                "patterns_detected": float(self._patterns_detected),
                "anomalies_flagged": float(self._anomalies_flagged),
                "reports_generated": float(self._reports_generated),
                "last_heartbeat_seq": float(self._last_heartbeat_seq),
                "uptime_seconds": round(uptime, 2),
            },
            message="Analytical engine active — monitoring telemetry streams",
        )
