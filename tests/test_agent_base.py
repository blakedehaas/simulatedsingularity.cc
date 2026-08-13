"""Tests for the CognitiveNode ABC and core data models."""

from __future__ import annotations

import pytest

from singularity.neural_core.node_base import (
    CognitiveOutput,
    NodeStatus,
    CognitiveNode,
    SystemPulse,
    C2InterventionRequest,
    InterruptResolution,
    ActionProposal,
    SynapticTransmission,
    RiskLevel,
    DiagnosticFrame,
)


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------

class TestPromptPayload:
    """Tests for the SynapticTransmission data model."""

    def test_creation_with_defaults(self) -> None:
        """SynapticTransmission should auto-generate ID and timestamp."""
        payload = SynapticTransmission(
            source_node_id="agent-a",
            target_node_id="agent-b",
            content="Hello",
        )
        assert payload.payload_id
        assert payload.timestamp is not None
        assert payload.source_node_id == "agent-a"
        assert payload.target_node_id == "agent-b"
        assert payload.content == "Hello"
        assert payload.metadata == {}

    def test_creation_with_metadata(self) -> None:
        """SynapticTransmission should accept arbitrary metadata."""
        payload = SynapticTransmission(
            source_node_id="a",
            target_node_id="b",
            content="test",
            metadata={"priority": "high", "retry_count": 3},
        )
        assert payload.metadata["priority"] == "high"
        assert payload.metadata["retry_count"] == 3


class TestTelemetryFrame:
    """Tests for the DiagnosticFrame data model."""

    def test_default_status(self) -> None:
        """DiagnosticFrame should default to NOMINAL status."""
        frame = DiagnosticFrame(node_id="test-001")
        assert frame.status == NodeStatus.NOMINAL
        assert frame.metrics == {}
        assert frame.message == ""

    def test_with_metrics(self) -> None:
        """DiagnosticFrame should store arbitrary float metrics."""
        frame = DiagnosticFrame(
            node_id="test-001",
            status=NodeStatus.BUSY,
            metrics={"cpu": 45.2, "queue_depth": 3.0},
            message="Processing heavy workload",
        )
        assert frame.metrics["cpu"] == 45.2
        assert frame.status == NodeStatus.BUSY


class TestProposedAction:
    """Tests for the ActionProposal data model."""

    def test_default_risk_level(self) -> None:
        """ActionProposal should default to LOW risk."""
        action = ActionProposal(
            node_id="test-001",
            action_type="read",
            description="Read configuration file",
        )
        assert action.risk_level == RiskLevel.LOW

    def test_all_risk_levels(self) -> None:
        """All risk levels should be valid enum values."""
        for level in RiskLevel:
            action = ActionProposal(
                node_id="test",
                action_type="test",
                description="test",
                risk_level=level,
            )
            assert action.risk_level == level


class TestInterruptRequest:
    """Tests for the C2InterventionRequest data model."""

    def test_default_pending(self) -> None:
        """C2InterventionRequest should default to PENDING resolution."""
        action = ActionProposal(
            node_id="test",
            action_type="write",
            description="Write to disk",
            risk_level=RiskLevel.HIGH,
        )
        interrupt = C2InterventionRequest(proposed_action=action)
        assert interrupt.resolution == InterruptResolution.PENDING
        assert interrupt.resolved_by is None
        assert interrupt.resolved_at is None


class TestHeartbeatEvent:
    """Tests for the SystemPulse data model."""

    def test_creation(self) -> None:
        """SystemPulse should store sequence number and summary."""
        event = SystemPulse(
            sequence_number=42,
            constellation_summary={
                "agent-a": NodeStatus.NOMINAL,
                "agent-b": NodeStatus.BUSY,
            },
        )
        assert event.sequence_number == 42
        assert len(event.constellation_summary) == 2


class TestAgentResponse:
    """Tests for the CognitiveOutput data model."""

    def test_creation(self) -> None:
        """CognitiveOutput should aggregate content, telemetry, and actions."""
        telemetry = DiagnosticFrame(node_id="test")
        action = ActionProposal(
            node_id="test",
            action_type="exec",
            description="Run command",
        )
        response = CognitiveOutput(
            node_id="test",
            content="Task completed",
            telemetry=telemetry,
            action_proposals=[action],
        )
        assert response.content == "Task completed"
        assert len(response.action_proposals) == 1
        assert response.telemetry.node_id == "test"


# ---------------------------------------------------------------------------
# CognitiveNode ABC tests
# ---------------------------------------------------------------------------

class TestAsyncBaseNode:
    """Tests for the CognitiveNode abstract base class."""

    def test_cannot_instantiate_abc(self) -> None:
        """CognitiveNode should not be directly instantiable."""
        with pytest.raises(TypeError):
            CognitiveNode(  # type: ignore[abstract]
                node_id="test",
                node_name="Test",
                node_role="Testing",
            )

    def test_mock_agent_instantiation(self, mock_agent) -> None:
        """A concrete subclass should instantiate correctly."""
        assert mock_agent.node_id == "mock-001"
        assert mock_agent.node_name == "MockNode"
        assert mock_agent.node_role == "Testing"
        assert mock_agent.priority == 99
        assert mock_agent.status == NodeStatus.INITIALIZING

    @pytest.mark.asyncio
    async def test_receive_prompt(self, mock_agent, sample_prompt_payload) -> None:
        """receive_prompt should return an CognitiveOutput."""
        response = await mock_agent.receive_prompt(sample_prompt_payload)
        assert isinstance(response, CognitiveOutput)
        assert "Mock response" in response.content
        assert response.node_id == "mock-001"
        assert mock_agent._prompt_count == 1

    @pytest.mark.asyncio
    async def test_process_heartbeat(self, mock_agent, sample_heartbeat) -> None:
        """process_heartbeat should return a DiagnosticFrame."""
        frame = await mock_agent.process_heartbeat(sample_heartbeat)
        assert isinstance(frame, DiagnosticFrame)
        assert frame.node_id == "mock-001"
        assert mock_agent._pulse_count == 2

    @pytest.mark.asyncio
    async def test_process_heartbeat_compaction(self, mock_agent, sample_heartbeat) -> None:
        """process_heartbeat should compact scratchpad every 10 heartbeats."""
        from unittest.mock import AsyncMock, patch
        
        # Inject some scratchpad entries
        for i in range(15):
            mock_agent._scratchpad.append(f"Entry {i}")
            
        mock_agent._pulse_count = 9
        
        # We need a mock model with a `generate` method returning an object with a `content` attribute
        class DummyResp:
            content = "condensed summary"
            
        class DummyModel:
            async def generate(self, text: str):
                return DummyResp()
                
        mock_agent._model = DummyModel()
        
        # Ensure it works even if generate fails
        class ErrorModel:
            async def generate(self, text: str):
                raise Exception("API error")
                
        # Trigger compaction (9 -> 10)
        with patch("singularity.memory_vault.repository.NodeRepository.append_scratchpad_log", new_callable=AsyncMock):
            await mock_agent.process_heartbeat(sample_heartbeat)
            
        assert mock_agent._pulse_count == 1 # 0 from compaction + 1 from handle_heartbeat
        assert "[COMPACTED CONTEXT]: condensed summary" in mock_agent._scratchpad[0]
        
        # Test error path
        mock_agent._pulse_count = 9
        mock_agent._model = ErrorModel()
        with patch("singularity.memory_vault.repository.NodeRepository.append_scratchpad_log", new_callable=AsyncMock):
            await mock_agent.process_heartbeat(sample_heartbeat)
        assert mock_agent._pulse_count == 1

    @pytest.mark.asyncio
    async def test_emit_telemetry(self, mock_agent) -> None:
        """emit_telemetry should return current metrics."""
        frame = await mock_agent.emit_telemetry()
        assert isinstance(frame, DiagnosticFrame)
        assert frame.metrics["prompts_processed"] == 0.0

    @pytest.mark.asyncio
    async def test_request_interrupt(
        self, mock_agent, sample_proposed_action
    ) -> None:
        """request_interrupt should create an C2InterventionRequest."""
        interrupt = await mock_agent.request_interrupt(sample_proposed_action)
        assert isinstance(interrupt, C2InterventionRequest)
        assert interrupt.proposed_action == sample_proposed_action
        assert interrupt.resolution == InterruptResolution.PENDING
        assert interrupt.serialized_state["node_id"] == "mock-001"

    def test_set_status(self, mock_agent) -> None:
        """set_status should update the agent's status."""
        mock_agent.set_status(NodeStatus.NOMINAL)
        assert mock_agent.status == NodeStatus.NOMINAL
        mock_agent.set_status(NodeStatus.BUSY)
        assert mock_agent.status == NodeStatus.BUSY

    def test_repr(self, mock_agent) -> None:
        """__repr__ should include key agent attributes."""
        repr_str = repr(mock_agent)
        assert "MockNode" in repr_str
        assert "mock-001" in repr_str
        assert "99" in repr_str
