"""Tests for the AsyncBaseAgent ABC and core data models."""

from __future__ import annotations

import pytest

from singularity.core.agent_base import (
    AgentResponse,
    AgentStatus,
    AsyncBaseAgent,
    HeartbeatEvent,
    InterruptRequest,
    InterruptResolution,
    ProposedAction,
    PromptPayload,
    RiskLevel,
    TelemetryFrame,
)


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------

class TestPromptPayload:
    """Tests for the PromptPayload data model."""

    def test_creation_with_defaults(self) -> None:
        """PromptPayload should auto-generate ID and timestamp."""
        payload = PromptPayload(
            source_agent_id="agent-a",
            target_agent_id="agent-b",
            content="Hello",
        )
        assert payload.payload_id
        assert payload.timestamp is not None
        assert payload.source_agent_id == "agent-a"
        assert payload.target_agent_id == "agent-b"
        assert payload.content == "Hello"
        assert payload.metadata == {}

    def test_creation_with_metadata(self) -> None:
        """PromptPayload should accept arbitrary metadata."""
        payload = PromptPayload(
            source_agent_id="a",
            target_agent_id="b",
            content="test",
            metadata={"priority": "high", "retry_count": 3},
        )
        assert payload.metadata["priority"] == "high"
        assert payload.metadata["retry_count"] == 3


class TestTelemetryFrame:
    """Tests for the TelemetryFrame data model."""

    def test_default_status(self) -> None:
        """TelemetryFrame should default to NOMINAL status."""
        frame = TelemetryFrame(agent_id="test-001")
        assert frame.status == AgentStatus.NOMINAL
        assert frame.metrics == {}
        assert frame.message == ""

    def test_with_metrics(self) -> None:
        """TelemetryFrame should store arbitrary float metrics."""
        frame = TelemetryFrame(
            agent_id="test-001",
            status=AgentStatus.BUSY,
            metrics={"cpu": 45.2, "queue_depth": 3.0},
            message="Processing heavy workload",
        )
        assert frame.metrics["cpu"] == 45.2
        assert frame.status == AgentStatus.BUSY


class TestProposedAction:
    """Tests for the ProposedAction data model."""

    def test_default_risk_level(self) -> None:
        """ProposedAction should default to LOW risk."""
        action = ProposedAction(
            agent_id="test-001",
            action_type="read",
            description="Read configuration file",
        )
        assert action.risk_level == RiskLevel.LOW

    def test_all_risk_levels(self) -> None:
        """All risk levels should be valid enum values."""
        for level in RiskLevel:
            action = ProposedAction(
                agent_id="test",
                action_type="test",
                description="test",
                risk_level=level,
            )
            assert action.risk_level == level


class TestInterruptRequest:
    """Tests for the InterruptRequest data model."""

    def test_default_pending(self) -> None:
        """InterruptRequest should default to PENDING resolution."""
        action = ProposedAction(
            agent_id="test",
            action_type="write",
            description="Write to disk",
            risk_level=RiskLevel.HIGH,
        )
        interrupt = InterruptRequest(proposed_action=action)
        assert interrupt.resolution == InterruptResolution.PENDING
        assert interrupt.resolved_by is None
        assert interrupt.resolved_at is None


class TestHeartbeatEvent:
    """Tests for the HeartbeatEvent data model."""

    def test_creation(self) -> None:
        """HeartbeatEvent should store sequence number and summary."""
        event = HeartbeatEvent(
            sequence_number=42,
            constellation_summary={
                "agent-a": AgentStatus.NOMINAL,
                "agent-b": AgentStatus.BUSY,
            },
        )
        assert event.sequence_number == 42
        assert len(event.constellation_summary) == 2


class TestAgentResponse:
    """Tests for the AgentResponse data model."""

    def test_creation(self) -> None:
        """AgentResponse should aggregate content, telemetry, and actions."""
        telemetry = TelemetryFrame(agent_id="test")
        action = ProposedAction(
            agent_id="test",
            action_type="exec",
            description="Run command",
        )
        response = AgentResponse(
            agent_id="test",
            content="Task completed",
            telemetry=telemetry,
            proposed_actions=[action],
        )
        assert response.content == "Task completed"
        assert len(response.proposed_actions) == 1
        assert response.telemetry.agent_id == "test"


# ---------------------------------------------------------------------------
# AsyncBaseAgent ABC tests
# ---------------------------------------------------------------------------

class TestAsyncBaseAgent:
    """Tests for the AsyncBaseAgent abstract base class."""

    def test_cannot_instantiate_abc(self) -> None:
        """AsyncBaseAgent should not be directly instantiable."""
        with pytest.raises(TypeError):
            AsyncBaseAgent(  # type: ignore[abstract]
                agent_id="test",
                agent_name="Test",
                agent_role="Testing",
            )

    def test_mock_agent_instantiation(self, mock_agent) -> None:
        """A concrete subclass should instantiate correctly."""
        assert mock_agent.agent_id == "mock-001"
        assert mock_agent.agent_name == "MockAgent"
        assert mock_agent.agent_role == "Testing"
        assert mock_agent.priority == 99
        assert mock_agent.status == AgentStatus.INITIALIZING

    @pytest.mark.asyncio
    async def test_receive_prompt(self, mock_agent, sample_prompt_payload) -> None:
        """receive_prompt should return an AgentResponse."""
        response = await mock_agent.receive_prompt(sample_prompt_payload)
        assert isinstance(response, AgentResponse)
        assert "Mock response" in response.content
        assert response.agent_id == "mock-001"
        assert mock_agent._prompt_count == 1

    @pytest.mark.asyncio
    async def test_process_heartbeat(self, mock_agent, sample_heartbeat) -> None:
        """process_heartbeat should return a TelemetryFrame."""
        frame = await mock_agent.process_heartbeat(sample_heartbeat)
        assert isinstance(frame, TelemetryFrame)
        assert frame.agent_id == "mock-001"
        assert mock_agent._heartbeat_count == 1

    @pytest.mark.asyncio
    async def test_emit_telemetry(self, mock_agent) -> None:
        """emit_telemetry should return current metrics."""
        frame = await mock_agent.emit_telemetry()
        assert isinstance(frame, TelemetryFrame)
        assert frame.metrics["prompts_processed"] == 0.0

    @pytest.mark.asyncio
    async def test_request_interrupt(
        self, mock_agent, sample_proposed_action
    ) -> None:
        """request_interrupt should create an InterruptRequest."""
        interrupt = await mock_agent.request_interrupt(sample_proposed_action)
        assert isinstance(interrupt, InterruptRequest)
        assert interrupt.proposed_action == sample_proposed_action
        assert interrupt.resolution == InterruptResolution.PENDING
        assert interrupt.serialized_state["agent_id"] == "mock-001"

    def test_set_status(self, mock_agent) -> None:
        """set_status should update the agent's status."""
        mock_agent.set_status(AgentStatus.NOMINAL)
        assert mock_agent.status == AgentStatus.NOMINAL
        mock_agent.set_status(AgentStatus.BUSY)
        assert mock_agent.status == AgentStatus.BUSY

    def test_repr(self, mock_agent) -> None:
        """__repr__ should include key agent attributes."""
        repr_str = repr(mock_agent)
        assert "MockAgent" in repr_str
        assert "mock-001" in repr_str
        assert "99" in repr_str
