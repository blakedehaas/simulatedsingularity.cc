"""AsyncBaseAgent abstract base class and core data models.

Defines the standard interface that all orbital node agents in the
Simulated Singularity constellation must implement. Includes Pydantic
data models for inter-agent communication payloads.
"""

from __future__ import annotations

import enum
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class RiskLevel(str, enum.Enum):
    """Classification of risk for proposed agent actions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentStatus(str, enum.Enum):
    """Operational status of an orbital node agent."""

    INITIALIZING = "initializing"
    NOMINAL = "nominal"
    BUSY = "busy"
    INTERRUPTED = "interrupted"
    ERROR = "error"
    OFFLINE = "offline"


class InterruptResolution(str, enum.Enum):
    """Resolution outcome for an interrupt / sync prompt."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    MODIFIED = "modified"


# ---------------------------------------------------------------------------
# Data Models (Pydantic)
# ---------------------------------------------------------------------------

def _utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


def _new_id() -> str:
    """Generate a short unique identifier."""
    return uuid.uuid4().hex[:12]


class PromptPayload(BaseModel):
    """Timestamped message routed between agents or from Ground Control.

    Attributes:
        payload_id: Unique identifier for this payload.
        source_agent_id: ID of the sending agent (or ``"ground_control"``).
        target_agent_id: ID of the intended recipient agent.
        content: The textual content of the prompt.
        metadata: Arbitrary key-value metadata attached to the payload.
        timestamp: UTC timestamp when the payload was created.
    """

    payload_id: str = Field(default_factory=_new_id)
    source_agent_id: str
    target_agent_id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utc_now)


class TelemetryFrame(BaseModel):
    """Snapshot of an agent's operational telemetry at a point in time.

    Attributes:
        agent_id: The agent that emitted this frame.
        status: Current operational status.
        metrics: Key-value metrics (CPU usage, queue depth, etc.).
        message: Optional human-readable status message.
        timestamp: UTC timestamp of the telemetry capture.
    """

    agent_id: str
    status: AgentStatus = AgentStatus.NOMINAL
    metrics: dict[str, float] = Field(default_factory=dict)
    message: str = ""
    timestamp: datetime = Field(default_factory=_utc_now)


class HeartbeatEvent(BaseModel):
    """Periodic heartbeat broadcast by the Mission Planning scheduler.

    Dispatched every 60 seconds to synchronize the constellation.

    Attributes:
        sequence_number: Monotonically increasing heartbeat counter.
        timestamp: UTC timestamp of the heartbeat.
        constellation_summary: Snapshot of active agent statuses.
    """

    sequence_number: int
    timestamp: datetime = Field(default_factory=_utc_now)
    constellation_summary: dict[str, AgentStatus] = Field(default_factory=dict)


class ProposedAction(BaseModel):
    """A state-mutating action proposed by an agent that may require C2 approval.

    Attributes:
        action_id: Unique identifier for this proposed action.
        agent_id: The agent proposing the action.
        action_type: Category of the action (e.g., ``"tool_call"``, ``"state_write"``).
        description: Human-readable description of what the action does.
        parameters: Action-specific parameters.
        risk_level: Assessed risk level.
        timestamp: When the action was proposed.
    """

    action_id: str = Field(default_factory=_new_id)
    agent_id: str
    action_type: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    timestamp: datetime = Field(default_factory=_utc_now)


class InterruptRequest(BaseModel):
    """Request to pause graph execution for C2 review of a proposed action.

    Created when a ``ProposedAction`` triggers a LangGraph interrupt.

    Attributes:
        interrupt_id: Unique identifier for this interrupt.
        proposed_action: The action under review.
        serialized_state: JSON-serializable snapshot of the execution state.
        resolution: Current resolution status.
        resolved_by: Identifier of the operator who resolved (if any).
        resolved_at: Timestamp of resolution (if any).
    """

    interrupt_id: str = Field(default_factory=_new_id)
    proposed_action: ProposedAction
    serialized_state: dict[str, Any] = Field(default_factory=dict)
    resolution: InterruptResolution = InterruptResolution.PENDING
    resolved_by: str | None = None
    resolved_at: datetime | None = None


class AgentResponse(BaseModel):
    """Response produced by an agent after processing a prompt.

    Attributes:
        agent_id: The responding agent.
        content: Textual response content.
        telemetry: Current telemetry snapshot.
        proposed_actions: Any state-mutating actions the agent wants to perform.
        metadata: Arbitrary response metadata.
        timestamp: When the response was generated.
    """

    agent_id: str
    content: str
    telemetry: TelemetryFrame
    proposed_actions: list[ProposedAction] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utc_now)


# ---------------------------------------------------------------------------
# Abstract Base Class
# ---------------------------------------------------------------------------

class AsyncBaseAgent(ABC):
    """Abstract base class for all orbital node agents in the constellation.

    Every agent in the Simulated Singularity system must subclass this ABC
    and implement the three core async methods: :meth:`receive_prompt`,
    :meth:`process_heartbeat`, and :meth:`emit_telemetry`.

    Attributes:
        agent_id: Unique identifier for this agent instance.
        agent_name: Human-readable display name.
        agent_role: Description of the agent's operational role.
        priority: Routing priority (lower number = higher priority).
        status: Current operational status.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        agent_role: str,
        priority: int = 10,
    ) -> None:
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.agent_role = agent_role
        self.priority = priority
        self.status = AgentStatus.INITIALIZING
        self._created_at = _utc_now()
        self._scratchpad: list[str] = []
        self._heartbeat_count: int = 0

    # ------------------------------------------------------------------
    # Core abstract methods — must be implemented by every agent
    # ------------------------------------------------------------------

    async def receive_prompt(self, payload: PromptPayload) -> AgentResponse:
        """Process an incoming prompt payload with scratchpad context."""
        from singularity.persistence.repository import AgentRepository

        entry = f"Prompt received from {payload.source_agent_id}: {payload.content}"
        self._scratchpad.append(entry)
        await AgentRepository.append_scratchpad_log(self.agent_id, entry)

        # Inject scratchpad into model's system prompt temporarily if possible
        model = getattr(self, "_model", None)
        original_prompt = None
        if model and hasattr(model, "system_prompt"):
            original_prompt = model.system_prompt
            context_str = "\n".join(self._scratchpad)
            model.system_prompt = f"{original_prompt}\n\n[Agent Scratchpad Context]:\n{context_str}"

        try:
            response = await self.handle_prompt(payload)
        finally:
            if model and original_prompt is not None:
                model.system_prompt = original_prompt

        out_entry = f"Response: {response.content}"
        self._scratchpad.append(out_entry)
        await AgentRepository.append_scratchpad_log(self.agent_id, out_entry)

        return response

    @abstractmethod
    async def handle_prompt(self, payload: PromptPayload) -> AgentResponse:
        """Subclass implementation of prompt processing."""

    async def process_heartbeat(self, heartbeat: HeartbeatEvent) -> TelemetryFrame:
        """Process a heartbeat and handle scratchpad compaction."""
        from singularity.persistence.repository import AgentRepository

        entry = f"Heartbeat seq {heartbeat.sequence_number} received."
        self._scratchpad.append(entry)
        await AgentRepository.append_scratchpad_log(self.agent_id, entry)

        self._heartbeat_count += 1
        if self._heartbeat_count >= 10 and len(self._scratchpad) > 1:
            mid = len(self._scratchpad) // 2
            to_compact = "\n".join(self._scratchpad[:mid])
            
            model = getattr(self, "_model", None)
            if model and hasattr(model, "generate"):
                try:
                    summary_resp = await model.generate(
                        f"Summarize the following scratchpad entries concisely to condense context by half:\n{to_compact}"
                    )
                    compacted = f"[COMPACTED CONTEXT]: {summary_resp.content}"
                    self._scratchpad = [compacted] + self._scratchpad[mid:]
                    await AgentRepository.append_scratchpad_log(self.agent_id, f"Compacted scratchpad into: {compacted}")
                except Exception:
                    pass
            self._heartbeat_count = 0

        return await self.handle_heartbeat(heartbeat)

    @abstractmethod
    async def handle_heartbeat(self, heartbeat: HeartbeatEvent) -> TelemetryFrame:
        """Subclass implementation of heartbeat processing."""

    @abstractmethod
    async def emit_telemetry(self) -> TelemetryFrame:
        """Emit the agent's current telemetry data on demand.

        Returns:
            A ``TelemetryFrame`` snapshot of the agent's operational metrics.
        """

    # ------------------------------------------------------------------
    # Shared concrete methods
    # ------------------------------------------------------------------

    async def request_interrupt(
        self, action: ProposedAction
    ) -> InterruptRequest:
        """Signal that a state-mutating action requires C2 approval.

        Constructs an :class:`InterruptRequest` from the proposed action,
        capturing the current execution context for serialization.

        Args:
            action: The proposed action to be reviewed.

        Returns:
            An ``InterruptRequest`` ready for submission to the orchestration
            layer's interrupt handler.
        """
        return InterruptRequest(
            proposed_action=action,
            serialized_state={
                "agent_id": self.agent_id,
                "agent_status": self.status.value,
                "timestamp": _utc_now().isoformat(),
            },
        )

    def set_status(self, status: AgentStatus) -> None:
        """Update the agent's operational status.

        Args:
            status: The new status to set.
        """
        self.status = status

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"id={self.agent_id!r} "
            f"name={self.agent_name!r} "
            f"priority={self.priority} "
            f"status={self.status.value}>"
        )
