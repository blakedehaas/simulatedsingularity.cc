import pytest
from unittest.mock import patch

from singularity.cognitive_nodes.analytical_agent import AnalyticalNode
from singularity.cognitive_nodes.architect_node import ArchitectNode
from singularity.cognitive_nodes.nexus_node import NexusNode
from singularity.cognitive_nodes.genesis_node import GenesisNode
from singularity.cognitive_nodes.environment_agent import EnvironmentNode
from singularity.cognitive_nodes.memory_agent import MemoryNode
from singularity.cognitive_nodes.synapse_node import SynapseNode
from singularity.cognitive_nodes.firewall_node import FirewallNode

@pytest.mark.asyncio
async def test_all_agents_init():
    with patch("singularity.neural_core.models.GeminiCognitionModel"):
        a1 = AnalyticalNode()
        a2 = ArchitectNode()
        a3 = NexusNode()
        a4 = GenesisNode()
        a5 = EnvironmentNode()
        a6 = MemoryNode()
        a7 = SynapseNode()
        a8 = FirewallNode()
        
        assert a1.node_id == "analytical-001"
        assert a2.node_id == "coding-001"
