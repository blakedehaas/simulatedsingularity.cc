import pytest
from unittest.mock import patch

from singularity.agents.analytical_agent import AnalyticalAgent
from singularity.agents.coding_agent import CodingAgent
from singularity.agents.core_agent import CoreAgent
from singularity.agents.creative_agent import CreativeAgent
from singularity.agents.environment_agent import EnvironmentAgent
from singularity.agents.memory_agent import MemoryAgent
from singularity.agents.prompt_agent import PromptAgent
from singularity.agents.security_agent import SecurityAgent

@pytest.mark.asyncio
async def test_all_agents_init():
    with patch("singularity.core.models.GemmaChatModel"):
        a1 = AnalyticalAgent()
        a2 = CodingAgent()
        a3 = CoreAgent()
        a4 = CreativeAgent()
        a5 = EnvironmentAgent()
        a6 = MemoryAgent()
        a7 = PromptAgent()
        a8 = SecurityAgent()
        
        assert a1.agent_id == "analytical-001"
        assert a2.agent_id == "coding-001"
