"""CognitiveNode abstract base class and core data models.

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


class NodeStatus(str, enum.Enum):
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


class SynapticTransmission(BaseModel):
    """Timestamped message routed between agents or from Ground Control.

    Attributes:
        payload_id: Unique identifier for this payload.
        source_node_id: ID of the sending agent (or ``"ground_control"``).
        target_node_id: ID of the intended recipient agent.
        content: The textual content of the prompt.
        metadata: Arbitrary key-value metadata attached to the payload.
        timestamp: UTC timestamp when the payload was created.
    """

    payload_id: str = Field(default_factory=_new_id)
    source_node_id: str
    target_node_id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utc_now)


class DiagnosticFrame(BaseModel):
    """Snapshot of an agent's operational telemetry at a point in time.

    Attributes:
        node_id: The agent that emitted this frame.
        status: Current operational status.
        metrics: Key-value metrics (CPU usage, queue depth, etc.).
        message: Optional human-readable status message.
        timestamp: UTC timestamp of the telemetry capture.
    """

    node_id: str
    status: NodeStatus = NodeStatus.NOMINAL
    metrics: dict[str, float] = Field(default_factory=dict)
    message: str = ""
    timestamp: datetime = Field(default_factory=_utc_now)


class SystemPulse(BaseModel):
    """Periodic heartbeat broadcast by the Mission Planning scheduler.

    Dispatched every 60 seconds to synchronize the constellation.

    Attributes:
        sequence_number: Monotonically increasing heartbeat counter.
        timestamp: UTC timestamp of the heartbeat.
        constellation_summary: Snapshot of active agent statuses.
    """

    sequence_number: int
    timestamp: datetime = Field(default_factory=_utc_now)
    constellation_summary: dict[str, NodeStatus] = Field(default_factory=dict)


class ActionProposal(BaseModel):
    """A state-mutating action proposed by an agent that may require C2 approval.

    Attributes:
        action_id: Unique identifier for this proposed action.
        node_id: The agent proposing the action.
        action_type: Category of the action (e.g., ``"tool_call"``, ``"state_write"``).
        description: Human-readable description of what the action does.
        parameters: Action-specific parameters.
        risk_level: Assessed risk level.
        timestamp: When the action was proposed.
    """

    action_id: str = Field(default_factory=_new_id)
    node_id: str
    action_type: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    timestamp: datetime = Field(default_factory=_utc_now)


class C2InterventionRequest(BaseModel):
    """Request to pause graph execution for C2 review of a proposed action.

    Created when a ``ActionProposal`` triggers a LangGraph interrupt.

    Attributes:
        interrupt_id: Unique identifier for this interrupt.
        proposed_action: The action under review.
        serialized_state: JSON-serializable snapshot of the execution state.
        resolution: Current resolution status.
        resolved_by: Identifier of the operator who resolved (if any).
        resolved_at: Timestamp of resolution (if any).
    """

    interrupt_id: str = Field(default_factory=_new_id)
    proposed_action: ActionProposal
    serialized_state: dict[str, Any] = Field(default_factory=dict)
    resolution: InterruptResolution = InterruptResolution.PENDING
    resolved_by: str | None = None
    resolved_at: datetime | None = None


class SynapticWeightFeedback(BaseModel):
    """Feedback emitted by an agent to adjust the dynamic weight/affinity with another agent.

    Attributes:
        source_node_id: The agent issuing the feedback.
        target_node_id: The agent being evaluated.
        utility_score: A float (e.g., -1.0 to 1.0) indicating the usefulness of the target's output.
        reason: Optional text explanation for the feedback.
        timestamp: When the feedback was generated.
    """

    source_node_id: str
    target_node_id: str
    utility_score: float
    reason: str = ""
    timestamp: datetime = Field(default_factory=_utc_now)


class CognitiveOutput(BaseModel):
    """Response produced by an agent after processing a prompt.

    Attributes:
        node_id: The responding agent.
        content: Textual response content.
        telemetry: Current telemetry snapshot.
        proposed_actions: Any state-mutating actions the agent wants to perform.
        connection_feedback: Feedback to update graph routing weights.
        metadata: Arbitrary response metadata.
        timestamp: When the response was generated.
    """

    node_id: str
    content: str
    telemetry: DiagnosticFrame
    proposed_actions: list[ActionProposal] = Field(default_factory=list)
    connection_feedback: list[SynapticWeightFeedback] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utc_now)


# ---------------------------------------------------------------------------
# Abstract Base Class
# ---------------------------------------------------------------------------

class CognitiveNode(ABC):
    """Abstract base class for all orbital node agents in the constellation.

    Every agent in the Simulated Singularity system must subclass this ABC
    and implement the three core async methods: :meth:`receive_prompt`,
    :meth:`process_heartbeat`, and :meth:`emit_telemetry`.

    Attributes:
        node_id: Unique identifier for this agent instance.
        node_name: Human-readable display name.
        node_role: Description of the agent's operational role.
        priority: Routing priority (lower number = higher priority).
        status: Current operational status.
    """

    def __init__(
        self,
        node_id: str,
        node_name: str,
        node_role: str,
        priority: int = 10,
        reflective_tools: list[Any] | None = None,
    ) -> None:
        self.node_id = node_id
        self.node_name = node_name
        self.node_role = node_role
        self.priority = priority
        self.status = NodeStatus.INITIALIZING
        self._created_at = _utc_now()
        self._scratchpad: list[str] = []
        self._heartbeat_count: int = 0
        
        from singularity.neural_core.models import GemmaChatModel
        self._reflective_model = GemmaChatModel(
            node_role=f"{node_role}_reflective",
            system_prompt=(
                f"You are the internal reflective cognitive layer for {node_name} ({node_id}). "
                "Before your operational layer decides how to respond externally, you must analyze the situation, "
                "formulate a plan, and use any available tools to gather necessary context. "
                "Your output will be kept private in your internal scratchpad."
            ),
            tools=reflective_tools
        )

    # ------------------------------------------------------------------
    # Core abstract methods — must be implemented by every agent
    # ------------------------------------------------------------------

    async def receive_prompt(self, payload: SynapticTransmission) -> CognitiveOutput:
        """Process an incoming prompt payload with scratchpad context."""
        from singularity.memory_vault.repository import AgentRepository

        entry = f"Prompt received from {payload.source_node_id}: {payload.content}"
        self._scratchpad.append(entry)
        await AgentRepository.append_scratchpad_log(self.node_id, entry)

        # ------------------------------------------------------------------
        # Reflective Phase
        # ------------------------------------------------------------------
        reflection_prompt = f"Analyze this incoming prompt and gather context using tools if necessary:\n{payload.content}"
        original_reflective_prompt = self._reflective_model.system_prompt
        context_str = "\n".join(self._scratchpad)
        
        self._reflective_model.system_prompt = f"{original_reflective_prompt}\n\n[Agent Scratchpad Context]:\n{context_str}"
        
        try:
            reflection = await self._reflective_model.generate(reflection_prompt)
        except Exception as e:
            reflection = f"Reflection generation failed: {e}"
        finally:
            self._reflective_model.system_prompt = original_reflective_prompt
            
        reflection_entry = f"[INTERNAL REFLECTION]: {reflection}"
        self._scratchpad.append(reflection_entry)
        await AgentRepository.append_scratchpad_log(self.node_id, reflection_entry)

        # ------------------------------------------------------------------
        # Operational Phase
        # ------------------------------------------------------------------
        # Inject scratchpad into model's system prompt temporarily if possible
        model = getattr(self, "_model", None)
        original_prompt = None
        if model and hasattr(model, "system_prompt"):
            original_prompt = model.system_prompt
            # Update context_str to include the reflection we just added
            context_str = "\n".join(self._scratchpad)
            
            oversight_prompt = ""
            leaders = payload.metadata.get("leaders", [])
            if self.node_id in leaders:
                oversight_prompt = "\nYou have emerged as the central consensus node of your cluster. Your role is now Oversight and Alignment. Synthesize the incoming intelligence from your subordinates and direct the hive toward the global objective.\n"
                
            model.system_prompt = f"{original_prompt}{oversight_prompt}\n\n[Agent Scratchpad Context]:\n{context_str}"

        try:
            response = await self.handle_prompt(payload)
        finally:
            if model and original_prompt is not None:
                model.system_prompt = original_prompt

        out_entry = f"Response: {response.content}"
        self._scratchpad.append(out_entry)
        await AgentRepository.append_scratchpad_log(self.node_id, out_entry)

        return response

    @abstractmethod
    async def handle_prompt(self, payload: SynapticTransmission) -> CognitiveOutput:
        """Subclass implementation of prompt processing."""

    async def process_heartbeat(self, heartbeat: SystemPulse) -> DiagnosticFrame:
        """Process a heartbeat and handle scratchpad compaction."""
        from singularity.memory_vault.repository import AgentRepository

        entry = f"Heartbeat seq {heartbeat.sequence_number} received."
        self._scratchpad.append(entry)
        await AgentRepository.append_scratchpad_log(self.node_id, entry)

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
                    await AgentRepository.append_scratchpad_log(self.node_id, f"Compacted scratchpad into: {compacted}")
                except Exception:
                    pass
            self._heartbeat_count = 0

        return await self.handle_heartbeat(heartbeat)

    @abstractmethod
    async def handle_heartbeat(self, heartbeat: SystemPulse) -> DiagnosticFrame:
        """Subclass implementation of heartbeat processing."""

    @abstractmethod
    async def emit_telemetry(self) -> DiagnosticFrame:
        """Emit the agent's current telemetry data on demand.

        Returns:
            A ``DiagnosticFrame`` snapshot of the agent's operational metrics.
        """

    # ------------------------------------------------------------------
    # Shared concrete methods
    # ------------------------------------------------------------------

    async def request_interrupt(
        self, action: ActionProposal
    ) -> C2InterventionRequest:
        """Signal that a state-mutating action requires C2 approval.

        Constructs an :class:`C2InterventionRequest` from the proposed action,
        capturing the current execution context for serialization.

        Args:
            action: The proposed action to be reviewed.

        Returns:
            An ``C2InterventionRequest`` ready for submission to the orchestration
            layer's interrupt handler.
        """
        return C2InterventionRequest(
            proposed_action=action,
            serialized_state={
                "node_id": self.node_id,
                "agent_status": self.status.value,
                "timestamp": _utc_now().isoformat(),
            },
        )

    def set_status(self, status: NodeStatus) -> None:
        """Update the agent's operational status.

        Args:
            status: The new status to set.
        """
        self.status = status

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"id={self.node_id!r} "
            f"name={self.node_name!r} "
            f"priority={self.priority} "
            f"status={self.status.value}>"
        )
