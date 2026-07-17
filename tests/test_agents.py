"""Tests for the SimulatedChatModel and agent registry."""

from __future__ import annotations

import pytest

from singularity.core.agent_base import AgentStatus, AsyncBaseAgent
from singularity.core.agent_registry import (
    get_agent,
    get_all_agents,
    get_registered_classes,
    initialize_constellation,
    register_agent,
    reset_registry,
)
from singularity.core.models import SimulatedChatModel


# ---------------------------------------------------------------------------
# SimulatedChatModel tests
# ---------------------------------------------------------------------------

class TestSimulatedChatModel:
    """Tests for the keyword-driven simulated chat model."""

    @pytest.mark.asyncio
    async def test_security_threat_keyword(self) -> None:
        """Security model should detect 'threat' keyword."""
        model = SimulatedChatModel(agent_role="security", response_delay=0)
        response = await model.generate("Detected a potential threat in sector 7")
        assert "THREAT DETECTED" in response

    @pytest.mark.asyncio
    async def test_security_hack_keyword(self) -> None:
        """Security model should detect 'hack' keyword."""
        model = SimulatedChatModel(agent_role="security", response_delay=0)
        response = await model.generate("Someone tried to hack the system")
        assert "CRITICAL ALERT" in response

    @pytest.mark.asyncio
    async def test_security_default(self) -> None:
        """Security model should return CLEAR for unmatched input."""
        model = SimulatedChatModel(agent_role="security", response_delay=0)
        response = await model.generate("Normal operations report")
        assert "CLEAR" in response

    @pytest.mark.asyncio
    async def test_core_agent_routing(self) -> None:
        """Core model should respond to 'route' keyword."""
        model = SimulatedChatModel(agent_role="core", response_delay=0)
        response = await model.generate("Please route this to analytics")
        assert "Routing" in response

    @pytest.mark.asyncio
    async def test_environment_health(self) -> None:
        """Environment model should respond to 'health' keyword."""
        model = SimulatedChatModel(agent_role="environment", response_delay=0)
        response = await model.generate("Check system health status")
        assert "NOMINAL" in response

    @pytest.mark.asyncio
    async def test_memory_store(self) -> None:
        """Memory model should respond to 'store' keyword."""
        model = SimulatedChatModel(agent_role="memory", response_delay=0)
        response = await model.generate("Store this data point")
        assert "committed" in response

    @pytest.mark.asyncio
    async def test_coding_generate(self) -> None:
        """Coding model should respond to 'generate' keyword."""
        model = SimulatedChatModel(agent_role="coding", response_delay=0)
        response = await model.generate("Generate a new module")
        assert "generation complete" in response.lower() or "Code generation" in response

    @pytest.mark.asyncio
    async def test_analytical_anomaly(self) -> None:
        """Analytical model should respond to 'anomaly' keyword."""
        model = SimulatedChatModel(agent_role="analytical", response_delay=0)
        response = await model.generate("Found an anomaly in the data")
        assert "Anomaly" in response

    @pytest.mark.asyncio
    async def test_creative_brainstorm(self) -> None:
        """Creative model should respond to 'brainstorm' keyword."""
        model = SimulatedChatModel(agent_role="creative", response_delay=0)
        response = await model.generate("Let's brainstorm solutions")
        assert "Brainstorming" in response

    @pytest.mark.asyncio
    async def test_unknown_role_fallback(self) -> None:
        """Unknown role should fall back to core templates."""
        model = SimulatedChatModel(agent_role="unknown_role", response_delay=0)
        response = await model.generate("route this message")
        assert "Routing" in response

    def test_sync_generation(self) -> None:
        """generate_sync should work without async context."""
        model = SimulatedChatModel(agent_role="security", response_delay=0)
        response = model.generate_sync("Check for a threat")
        assert "THREAT" in response

    def test_repr(self) -> None:
        """__repr__ should include role and delay."""
        model = SimulatedChatModel(agent_role="security", response_delay=0.1)
        assert "security" in repr(model)
        assert "0.1" in repr(model)


# ---------------------------------------------------------------------------
# Agent registry tests
# ---------------------------------------------------------------------------

class TestAgentRegistry:
    """Tests for the agent registration and lifecycle system."""

    def test_register_agent_decorator(self, mock_agent) -> None:
        """@register_agent should add class to the registry."""
        from tests.conftest import MockAgent

        register_agent(MockAgent)
        classes = get_registered_classes()
        assert "mock-001" in classes
        assert classes["mock-001"] is MockAgent

    def test_duplicate_registration_raises(self) -> None:
        """Registering the same AGENT_ID twice should raise ValueError."""
        from tests.conftest import MockAgent

        register_agent(MockAgent)
        with pytest.raises(ValueError, match="already registered"):
            register_agent(MockAgent)

    def test_missing_agent_id_raises(self) -> None:
        """Agent class without AGENT_ID should raise ValueError."""

        class BadAgent(AsyncBaseAgent):
            async def receive_prompt(self, payload):
                pass

            async def process_heartbeat(self, heartbeat):
                pass

            async def emit_telemetry(self):
                pass

        with pytest.raises(ValueError, match="AGENT_ID"):
            register_agent(BadAgent)

    def test_initialize_constellation(self) -> None:
        """initialize_constellation should create instances of all registered classes."""
        from tests.conftest import MockAgent

        register_agent(MockAgent)
        agents = initialize_constellation()
        assert len(agents) == 1
        assert agents[0].agent_id == "mock-001"
        assert agents[0].status == AgentStatus.NOMINAL

    def test_get_agent_by_id(self) -> None:
        """get_agent should return the correct instance."""
        from tests.conftest import MockAgent

        register_agent(MockAgent)
        initialize_constellation()
        agent = get_agent("mock-001")
        assert agent.agent_name == "MockAgent"

    def test_get_agent_not_found(self) -> None:
        """get_agent should raise KeyError for unknown ID."""
        with pytest.raises(KeyError, match="nonexistent"):
            get_agent("nonexistent")

    def test_get_all_agents_ordered(self) -> None:
        """get_all_agents should return agents ordered by priority."""
        from tests.conftest import MockAgent

        # Create two agent classes with different priorities
        class HighPriorityAgent(MockAgent):
            AGENT_ID = "high-001"

            def __init__(self, **kwargs):
                super().__init__(
                    agent_id="high-001",
                    agent_name="HighPriority",
                    priority=1,
                )

        class LowPriorityAgent(MockAgent):
            AGENT_ID = "low-001"

            def __init__(self, **kwargs):
                super().__init__(
                    agent_id="low-001",
                    agent_name="LowPriority",
                    priority=50,
                )

        register_agent(HighPriorityAgent)
        register_agent(LowPriorityAgent)
        initialize_constellation()

        agents = get_all_agents()
        assert agents[0].priority < agents[1].priority
        assert agents[0].agent_id == "high-001"

    def test_reset_registry(self) -> None:
        """reset_registry should clear all classes and instances."""
        from tests.conftest import MockAgent

        register_agent(MockAgent)
        initialize_constellation()
        assert len(get_all_agents()) == 1

        reset_registry()
        assert len(get_registered_classes()) == 0
        assert len(get_all_agents()) == 0
