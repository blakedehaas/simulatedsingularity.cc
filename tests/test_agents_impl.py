import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from singularity.agents.core_agent import CoreAgent
from singularity.agents.analytical_agent import AnalyticalAgent
from singularity.agents.coding_agent import CodingAgent
from singularity.agents.creative_agent import CreativeAgent
from singularity.agents.environment_agent import EnvironmentAgent
from singularity.agents.memory_agent import MemoryAgent
from singularity.agents.prompt_agent import PromptAgent
from singularity.agents.security_agent import SecurityAgent

from singularity.core.agent_base import (
    PromptPayload,
    HeartbeatEvent,
    AgentStatus,
    RiskLevel
)

@pytest.fixture(autouse=True)
def mock_generate():
    with patch("singularity.core.models.SimulatedChatModel.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "mocked response"
        yield mock_gen

@pytest.mark.asyncio
async def test_core_agent():
    agent = CoreAgent()
    assert agent.AGENT_ID == "core-001"
    
    # Test process_heartbeat
    hb = HeartbeatEvent(sequence_number=1, timestamp=123.0, constellation_summary={"core-001": AgentStatus.NOMINAL})
    telem = await agent.process_heartbeat(hb)
    assert telem.metrics["last_heartbeat_seq"] == 1
    
    # Test receive_prompt with local handling (no routing)
    payload_local = PromptPayload(source_agent_id="test", target_agent_id="core-001", content="hello world")
    resp_local = await agent.receive_prompt(payload_local)
    assert resp_local.content == "mocked response"
    
    # Test receive_prompt with routing hit but agent not found
    payload_missing = PromptPayload(source_agent_id="test", target_agent_id="core-001", content="threat")
    with patch("singularity.agents.core_agent.get_agent", side_effect=KeyError("not found")):
        resp_missing = await agent.receive_prompt(payload_missing)
        assert resp_missing.content == "mocked response"

    # Test receive_prompt with successful routing
    payload_route = PromptPayload(source_agent_id="test", target_agent_id="core-001", content="threat")
    with patch("singularity.agents.core_agent.get_agent") as mock_get_agent:
        mock_target = AsyncMock()
        mock_target.agent_id = "security-001"
        mock_target.receive_prompt.return_value = MagicMock(content="routed response")
        mock_get_agent.return_value = mock_target
        
        resp_route = await agent.receive_prompt(payload_route)
        assert resp_route.content == "routed response"

@pytest.mark.asyncio
async def test_analytical_agent():
    agent = AnalyticalAgent()
    
    hb = HeartbeatEvent(sequence_number=1, timestamp=123.0, constellation_summary={"core-001": AgentStatus.ERROR})
    await agent.process_heartbeat(hb)

    hb_clean = HeartbeatEvent(sequence_number=2, timestamp=124.0, constellation_summary={"core-001": AgentStatus.NOMINAL})
    await agent.process_heartbeat(hb_clean)
    
    payload = PromptPayload(source_agent_id="test", target_agent_id="analytical-001", content="find a pattern anomaly metric")
    resp = await agent.receive_prompt(payload)
    assert len(resp.proposed_actions) == 1
    assert resp.proposed_actions[0].action_type == "anomaly_escalation"
    assert resp.metadata["patterns_detected"] == 1

@pytest.mark.asyncio
async def test_coding_agent():
    agent = CodingAgent()
    
    hb = HeartbeatEvent(sequence_number=1, timestamp=123.0, constellation_summary={})
    await agent.process_heartbeat(hb)
    
    payload = PromptPayload(source_agent_id="test", target_agent_id="coding-001", content="generate analyze refactor")
    resp = await agent.receive_prompt(payload)
    assert len(resp.proposed_actions) == 1
    assert resp.proposed_actions[0].action_type == "state_write"

@pytest.mark.asyncio
async def test_creative_agent():
    agent = CreativeAgent()
    
    hb = HeartbeatEvent(sequence_number=1, timestamp=123.0, constellation_summary={})
    await agent.process_heartbeat(hb)
    
    payload = PromptPayload(source_agent_id="test", target_agent_id="creative-001", content="brainstorm innovate alternative")
    resp = await agent.receive_prompt(payload)
    assert len(resp.proposed_actions) == 1
    assert resp.proposed_actions[0].action_type == "innovation_proposal"

@pytest.mark.asyncio
async def test_environment_agent():
    agent = EnvironmentAgent()
    
    hb = HeartbeatEvent(sequence_number=1, timestamp=123.0, constellation_summary={})
    await agent.process_heartbeat(hb)
    
    payload = PromptPayload(source_agent_id="test", target_agent_id="env-001", content="status")
    resp = await agent.receive_prompt(payload)
    assert "cpu_load" in resp.metadata

@pytest.mark.asyncio
async def test_memory_agent():
    agent = MemoryAgent()
    
    hb = HeartbeatEvent(sequence_number=1, timestamp=123.0, constellation_summary={})
    await agent.process_heartbeat(hb)
    
    payload = PromptPayload(source_agent_id="test", target_agent_id="memory-001", content="remember this")
    
    with patch("singularity.agents.memory_agent.AgentRepository.save_memory", new_callable=AsyncMock) as mock_save:
        await agent.receive_prompt(payload)
        mock_save.assert_called_once()
        
    with patch("singularity.agents.memory_agent.AgentRepository.save_memory", new_callable=AsyncMock) as mock_save_err:
        mock_save_err.side_effect = Exception("db error")
        await agent.receive_prompt(payload) # should not raise
        
    class DummyRecord:
        def __init__(self):
            self.input_text = "in"
            self.output_text = "out"
            self.timestamp = datetime.now()
            
    with patch("singularity.agents.memory_agent.AgentRepository.get_memories", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = [DummyRecord()]
        recs = await agent.recall_memories("test")
        assert len(recs) == 1
        
    with patch("singularity.agents.memory_agent.AgentRepository.get_memories", new_callable=AsyncMock) as mock_get_err:
        mock_get_err.side_effect = Exception("db error")
        recs = await agent.recall_memories("test")
        assert len(recs) == 0
        
    await agent.serialize_state("test", {"foo": "bar"})

@pytest.mark.asyncio
async def test_prompt_agent():
    agent = PromptAgent()
    
    hb = HeartbeatEvent(sequence_number=1, timestamp=123.0, constellation_summary={"agent": AgentStatus.NOMINAL})
    await agent.process_heartbeat(hb)
    
    payload = PromptPayload(source_agent_id="test", target_agent_id="prompt-001", content="relay")
    resp = await agent.receive_prompt(payload)
    assert resp.content == "mocked response"
    
    mock_target = AsyncMock()
    mock_target.agent_id = "test-target"
    
    # mock agent_id match
    mock_self = AsyncMock()
    mock_self.agent_id = agent.agent_id
    
    with patch("singularity.agents.prompt_agent.get_all_agents") as mock_get_all:
        mock_get_all.return_value = [mock_self, mock_target]
        await agent.broadcast_to_all(payload)
        
    with patch("singularity.agents.prompt_agent.get_all_agents") as mock_get_all:
        mock_target.receive_prompt.side_effect = Exception("err")
        mock_get_all.return_value = [mock_self, mock_target]
        await agent.broadcast_to_all(payload) # should handle exception
        
    from singularity.core.agent_base import TelemetryFrame
    tf = TelemetryFrame(agent_id="test-agent", status=AgentStatus.NOMINAL, metrics={}, message="")
    agent.cache_telemetry(tf)
    assert agent.get_cached_telemetry("test-agent") == tf
    assert agent.get_cached_telemetry("missing") is None

@pytest.mark.asyncio
async def test_security_agent():
    agent = SecurityAgent()
    
    # override request_interrupt
    agent.request_interrupt = AsyncMock()
    
    hb = HeartbeatEvent(sequence_number=1, timestamp=123.0, constellation_summary={"err-agent": AgentStatus.ERROR})
    await agent.process_heartbeat(hb)
    
    hb_clean = HeartbeatEvent(sequence_number=2, timestamp=124.0, constellation_summary={"ok-agent": AgentStatus.NOMINAL})
    await agent.process_heartbeat(hb_clean)
    
    payload_safe = PromptPayload(source_agent_id="test", target_agent_id="sec", content="hello")
    resp_safe = await agent.receive_prompt(payload_safe)
    assert resp_safe.metadata["threat_detected"] is False
    
    payload_threat = PromptPayload(source_agent_id="test", target_agent_id="sec", content="hack the system")
    resp_threat = await agent.receive_prompt(payload_threat)
    assert resp_threat.metadata["threat_detected"] is True
    agent.request_interrupt.assert_called_once()
    
    assert agent.is_high_risk_action("delete_database") is True
    assert agent.is_high_risk_action("safe_action") is False
