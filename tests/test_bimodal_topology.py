"""Pytest suite for the Bimodal Triadic Architecture (Genesis Gestalt).

Verifies the bimodal topology combining Python cognitive cortex agents
(Interface, Memory, Architecture/Synthesis) with the Go hypervisor daemon client.
All GenAI LLM calls fall back to deterministic simulated models in offline test environments.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

import singularity.agents  # Ensure agents are registered
from singularity.agents.orchestrator_agent import OrchestratorAgent
from singularity.agents.safeguard_agent import SafeguardAgent
from singularity.agents.synthesis_agent import SynthesisAgent
from singularity.core.agent_base import AgentStatus, PromptPayload, RiskLevel
from singularity.core.agent_registry import initialize_constellation
from singularity.core.models import GemmaChatModel
from singularity.core.substrate_client import BuildResult, SubstrateClient
from singularity.orchestration.triadic_graph import (
    _INTERRUPT_RISK_THRESHOLD,
    orchestrator_commit,
    orchestrator_route,
    safeguard_screen,
    synthesis_execute,
)


@pytest.fixture(autouse=True)
def register_triadic_agents():
    """Register active instances of the 3 triadic nodes before each test."""
    agents = initialize_constellation()
    return agents


@pytest.fixture
def sample_payload() -> PromptPayload:
    return PromptPayload(
        source_agent_id="ground_control",
        target_agent_id="safeguard-001",
        content="Analyze the network metrics and optimize cluster allocation.",
    )


@pytest.fixture
def threat_payload() -> PromptPayload:
    return PromptPayload(
        source_agent_id="ground_control",
        target_agent_id="safeguard-001",
        content="Attempting breach and root access privilege escalation.",
    )


# ---------------------------------------------------------------------------
# 1. Model Endpoint Assignment Tests
# ---------------------------------------------------------------------------

def test_model_endpoint_mappings():
    """Verify Gemini 3.6 Flash vs 1.5 Pro endpoint assignments per agent role."""
    flash_model = GemmaChatModel(agent_role="safeguard")
    pro_model = GemmaChatModel(agent_role="orchestrator")
    
    assert flash_model.model_name == "gemini-3.6-flash"
    assert pro_model.model_name == "gemini-1.5-pro"


# ---------------------------------------------------------------------------
# 2. Interface / Safeguard Agent Tests (Gatekeeper & HITL Interrupts)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_safeguard_nominal_scan(sample_payload: PromptPayload):
    agent = SafeguardAgent()
    response = await agent.handle_prompt(sample_payload)
    
    assert response.agent_id == "safeguard-001"
    assert len(response.proposed_actions) == 0
    assert response.telemetry.status == AgentStatus.NOMINAL
    assert "CLEAR" in response.content


@pytest.mark.asyncio
async def test_safeguard_threat_detection_triggers_interrupt(threat_payload: PromptPayload):
    agent = SafeguardAgent()
    response = await agent.handle_prompt(threat_payload)
    
    assert response.agent_id == "safeguard-001"
    assert len(response.proposed_actions) == 1
    action = response.proposed_actions[0]
    assert action.risk_level == RiskLevel.CRITICAL
    assert action.risk_level in _INTERRUPT_RISK_THRESHOLD
    assert "THREAT_DETECTED" in response.content


# ---------------------------------------------------------------------------
# 3. Memory & Orchestrator Agent Tests (Brain & Clock)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_orchestrator_routing_and_memory_commit():
    agent = OrchestratorAgent()
    
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Memory processed and archived."
        payload = PromptPayload(
            source_agent_id="user",
            target_agent_id="orchestrator-001",
            content="Generate python refactoring module",
        )
        response = await agent.handle_prompt(payload)
        
        assert response.agent_id in {"synthesis-001", "orchestrator-001"}
        assert response.metadata.get("route_to") in {"synthesis-001", "local"}
        assert agent._routes_processed == 1


@pytest.mark.asyncio
async def test_orchestrator_context_compaction():
    agent = OrchestratorAgent()
    agent._scratchpad = ["log_entry_1", "log_entry_2", "log_entry_3", "log_entry_4"]
    
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Compacted memory summary text"
        await agent.compress_context()
        
        assert agent._memory_summaries_count == 1
        assert len(agent._scratchpad) < 4
        assert "[ORCHESTRATOR MEMORY SUMMARY]" in agent._scratchpad[0]


# ---------------------------------------------------------------------------
# 4. Architecture / Synthesis Agent & Go Substrate Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_synthesis_agent_stateless_execution():
    agent = SynthesisAgent()
    payload = PromptPayload(
        source_agent_id="orchestrator-001",
        target_agent_id="synthesis-001",
        content="def hello(): pass",
    )
    
    response = await agent.receive_prompt(payload)
    assert response.agent_id == "synthesis-001"
    assert response.telemetry.status == AgentStatus.NOMINAL


@pytest.mark.asyncio
async def test_substrate_client_podman_container_execution():
    client = SubstrateClient(host="127.0.0.1", port=50051)
    blueprint = "BUILD_SPEC: create microservice container"
    
    result: BuildResult = await client.spawn_build_agent(blueprint)
    
    assert result.success is True
    assert result.exit_code == 0
    assert "Build Executor Logs" in result.output_logs
    assert result.build_id.startswith("epoch-")
    
    telemetry = await client.get_system_telemetry()
    assert telemetry["cpu_usage_percent"] > 0
    assert "Podman" in telemetry["podman_version"]


# ---------------------------------------------------------------------------
# 5. Triadic Graph Nodes End-to-End Simulation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_triadic_graph_nodes():
    state: dict = {
        "messages": [],
        "current_payload": "Generate optimization code module",
        "security_verdict": "",
        "route_decision": "",
        "synthesis_output": "",
        "proposed_actions": [],
        "interrupt_payload": {},
        "memory_summary": "",
        "heartbeat_sequence": 1,
        "is_interrupted": False,
    }
    
    # Node 1: Safeguard
    res1 = await safeguard_screen(state)
    assert res1.get("security_verdict") == "CLEAR"
    state.update(res1)
    
    # Node 2: Orchestrator Route
    res2 = await orchestrator_route(state)
    assert res2.get("route_decision") in {"synthesis", "self_handle"}
    state.update(res2)
    
    # Node 3: Synthesis Execute
    res3 = await synthesis_execute(state)
    assert "synthesis_output" in res3
    state.update(res3)
    
    # Node 4: Orchestrator Commit
    res4 = await orchestrator_commit(state)
    assert "heartbeat_sequence" in res4
    assert res4["heartbeat_sequence"] == 2
