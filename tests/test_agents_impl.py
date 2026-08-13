import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from singularity.cognitive_nodes.nexus_node import NexusNode
from singularity.cognitive_nodes.analytical_agent import AnalyticalNode
from singularity.cognitive_nodes.architect_node import ArchitectNode
from singularity.cognitive_nodes.genesis_node import GenesisNode
from singularity.cognitive_nodes.environment_agent import EnvironmentNode
from singularity.cognitive_nodes.memory_agent import MemoryNode
from singularity.cognitive_nodes.synapse_node import SynapseNode
from singularity.cognitive_nodes.firewall_node import FirewallNode

from singularity.neural_core.node_base import (
    SynapticTransmission,
    SystemPulse,
    NodeStatus,
    RiskLevel
)

@pytest.fixture(autouse=True)
def mock_generate():
    with patch("singularity.neural_core.models.GeminiCognitionModel.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "mocked response"
        yield mock_gen

@pytest.mark.asyncio
async def test_core_agent():
    agent = NexusNode()
    assert agent.NODE_ID == "core-001"
    
    # Test process_heartbeat
    hb = SystemPulse(sequence_number=1, timestamp=123.0, constellation_summary={"core-001": NodeStatus.NOMINAL})
    telem = await agent.process_heartbeat(hb)
    assert telem.metrics["last_heartbeat_seq"] == 1
    
    # Test receive_prompt with local handling (no routing)
    payload_local = SynapticTransmission(source_node_id="test", target_node_id="core-001", content="hello world")
    resp_local = await agent.receive_prompt(payload_local)
    assert resp_local.content == "mocked response"
    
    # Test receive_prompt with routing hit but agent not found
    payload_missing = SynapticTransmission(source_node_id="test", target_node_id="core-001", content="threat")
    with patch("singularity.cognitive_nodes.nexus_node.get_node", side_effect=KeyError("not found")):
        resp_missing = await agent.receive_prompt(payload_missing)
        assert resp_missing.content == "mocked response"

    # Test receive_prompt with successful routing
    payload_route = SynapticTransmission(source_node_id="test", target_node_id="core-001", content="threat")
    with patch("singularity.cognitive_nodes.nexus_node.get_node") as mock_get_agent:
        mock_target = AsyncMock()
        mock_target.node_id = "security-001"
        mock_target.receive_prompt.return_value = MagicMock(content="routed response")
        mock_get_agent.return_value = mock_target
        
        resp_route = await agent.receive_prompt(payload_route)
        assert resp_route.content == "routed response"

@pytest.mark.asyncio
async def test_analytical_agent():
    agent = AnalyticalNode()
    
    hb = SystemPulse(sequence_number=1, timestamp=123.0, constellation_summary={"core-001": NodeStatus.ERROR})
    await agent.process_heartbeat(hb)

    hb_clean = SystemPulse(sequence_number=2, timestamp=124.0, constellation_summary={"core-001": NodeStatus.NOMINAL})
    await agent.process_heartbeat(hb_clean)
    
    payload = SynapticTransmission(source_node_id="test", target_node_id="analytical-001", content="find a pattern anomaly metric")
    resp = await agent.receive_prompt(payload)
    assert len(resp.action_proposals) == 1
    assert resp.action_proposals[0].action_type == "anomaly_escalation"
    assert resp.metadata["patterns_detected"] == 1

@pytest.mark.asyncio
async def test_coding_agent():
    agent = ArchitectNode()
    
    hb = SystemPulse(sequence_number=1, timestamp=123.0, constellation_summary={})
    await agent.process_heartbeat(hb)
    
    payload = SynapticTransmission(source_node_id="test", target_node_id="coding-001", content="generate analyze refactor")
    resp = await agent.receive_prompt(payload)
    assert len(resp.action_proposals) == 1
    assert resp.action_proposals[0].action_type == "state_write"

@pytest.mark.asyncio
async def test_creative_agent():
    agent = GenesisNode()
    
    hb = SystemPulse(sequence_number=1, timestamp=123.0, constellation_summary={})
    await agent.process_heartbeat(hb)
    
    payload = SynapticTransmission(source_node_id="test", target_node_id="creative-001", content="brainstorm innovate alternative")
    resp = await agent.receive_prompt(payload)
    assert len(resp.action_proposals) == 1
    assert resp.action_proposals[0].action_type == "innovation_proposal"

@pytest.mark.asyncio
async def test_environment_agent():
    agent = EnvironmentNode()
    
    hb = SystemPulse(sequence_number=1, timestamp=123.0, constellation_summary={})
    await agent.process_heartbeat(hb)
    
    payload = SynapticTransmission(source_node_id="test", target_node_id="env-001", content="status")
    resp = await agent.receive_prompt(payload)
    assert "cpu_load" in resp.metadata

@pytest.mark.asyncio
async def test_memory_agent():
    agent = MemoryNode()
    
    hb = SystemPulse(sequence_number=1, timestamp=123.0, constellation_summary={})
    await agent.process_heartbeat(hb)
    
    payload = SynapticTransmission(source_node_id="test", target_node_id="memory-001", content="remember this")
    
    with patch("singularity.cognitive_nodes.memory_agent.NodeRepository.save_memory", new_callable=AsyncMock) as mock_save:
        await agent.receive_prompt(payload)
        mock_save.assert_called_once()
        
    with patch("singularity.cognitive_nodes.memory_agent.NodeRepository.save_memory", new_callable=AsyncMock) as mock_save_err:
        mock_save_err.side_effect = Exception("db error")
        await agent.receive_prompt(payload) # should not raise
        
    class DummyRecord:
        def __init__(self):
            self.input_text = "in"
            self.output_text = "out"
            self.timestamp = datetime.now()
            
    with patch("singularity.cognitive_nodes.memory_agent.NodeRepository.get_memories", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = [DummyRecord()]
        recs = await agent.recall_memories("test")
        assert len(recs) == 1
        
    with patch("singularity.cognitive_nodes.memory_agent.NodeRepository.get_memories", new_callable=AsyncMock) as mock_get_err:
        mock_get_err.side_effect = Exception("db error")
        recs = await agent.recall_memories("test")
        assert len(recs) == 0
        
    await agent.serialize_state("test", {"foo": "bar"})

@pytest.mark.asyncio
async def test_prompt_agent():
    agent = SynapseNode()
    
    hb = SystemPulse(sequence_number=1, timestamp=123.0, constellation_summary={"agent": NodeStatus.NOMINAL})
    await agent.process_heartbeat(hb)
    
    payload = SynapticTransmission(source_node_id="test", target_node_id="prompt-001", content="relay")
    resp = await agent.receive_prompt(payload)
    assert resp.content == "mocked response"
    
    mock_target = AsyncMock()
    mock_target.node_id = "test-target"
    
    # mock node_id match
    mock_self = AsyncMock()
    mock_self.node_id = agent.node_id
    
    with patch("singularity.cognitive_nodes.synapse_node.get_all_nodes") as mock_get_all:
        mock_get_all.return_value = [mock_self, mock_target]
        await agent.broadcast_to_all(payload)
        
    with patch("singularity.cognitive_nodes.synapse_node.get_all_nodes") as mock_get_all:
        mock_target.receive_prompt.side_effect = Exception("err")
        mock_get_all.return_value = [mock_self, mock_target]
        await agent.broadcast_to_all(payload) # should handle exception
        
    from singularity.neural_core.node_base import DiagnosticFrame
    tf = DiagnosticFrame(node_id="test-agent", status=NodeStatus.NOMINAL, metrics={}, message="")
    agent.cache_diagnostics(tf)
    assert agent.get_cached_diagnostics("test-agent") == tf
    assert agent.get_cached_diagnostics("missing") is None

@pytest.mark.asyncio
async def test_security_agent():
    agent = FirewallNode()
    
    # override request_interrupt
    agent.request_interrupt = AsyncMock()
    
    hb = SystemPulse(sequence_number=1, timestamp=123.0, constellation_summary={"err-agent": NodeStatus.ERROR})
    await agent.process_heartbeat(hb)
    
    hb_clean = SystemPulse(sequence_number=2, timestamp=124.0, constellation_summary={"ok-agent": NodeStatus.NOMINAL})
    await agent.process_heartbeat(hb_clean)
    
    payload_safe = SynapticTransmission(source_node_id="test", target_node_id="sec", content="hello")
    resp_safe = await agent.receive_prompt(payload_safe)
    assert resp_safe.metadata["threat_detected"] is False
    
    payload_threat = SynapticTransmission(source_node_id="test", target_node_id="sec", content="hack the system")
    resp_threat = await agent.receive_prompt(payload_threat)
    assert resp_threat.metadata["threat_detected"] is True
    agent.request_interrupt.assert_called_once()
    
    assert agent.is_high_risk_action("delete_database") is True
    assert agent.is_high_risk_action("safe_action") is False
