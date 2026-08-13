import logging
from unittest.mock import MagicMock, patch
import pytest

from singularity.temporal.temporal_rag import (
    TemporalAgentNode,
    instantiate_temporal_agent,
    simulate_dialectic,
)

logger = logging.getLogger(__name__)

def test_instantiate_temporal_agent():
    """TRACE-TRAG-001: Test instantiation of TemporalAgentNode."""
    logger.debug("Testing instantiate_temporal_agent")
    
    agent = instantiate_temporal_agent(target_age=25, user_birth_year=1990)
    
    assert isinstance(agent, TemporalAgentNode)
    assert agent.age == 25
    assert agent.memory_filter == {"cutoff_year": 2015}

def test_temporal_agent_query_past(mock_temporal_vector_memory):
    """TRACE-TRAG-002: Test query_past utilizes memory filter and returns expected output."""
    logger.debug("Testing query_past")
    
    agent = instantiate_temporal_agent(target_age=30, user_birth_year=1980)
    
    result = agent.query_past("What was popular in high school?", mock_temporal_vector_memory)
    
    mock_temporal_vector_memory.retrieve_context.assert_called_once()
    args, kwargs = mock_temporal_vector_memory.retrieve_context.call_args
    
    assert kwargs.get("filter") == {"cutoff_year": 2010}
    assert "30" in str(result)
    assert isinstance(result, str)

def test_temporal_agent_cutoff_calculation():
    """TRACE-TRAG-003: Test cutoff calculation for multiple ages."""
    logger.debug("Testing cutoff year calculations")
    
    birth_year = 1990
    
    agent_18 = instantiate_temporal_agent(18, birth_year)
    assert agent_18.memory_filter["cutoff_year"] == 2008
    
    agent_25 = instantiate_temporal_agent(25, birth_year)
    assert agent_25.memory_filter["cutoff_year"] == 2015
    
    agent_40 = instantiate_temporal_agent(40, birth_year)
    assert agent_40.memory_filter["cutoff_year"] == 2030

@pytest.mark.asyncio
@patch('singularity.temporal.temporal_rag.genai.Client')
async def test_simulate_dialectic(mock_client_cls):
    """TRACE-TRAG-004: Test simulation of a dialectic conversation between two agents."""
    logger.debug("Testing simulate_dialectic")
    
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = "[Age 20]: Hello\n[Age 40]: Hi\n[Age 20]: How are you?\n[Age 40]: Good"
    mock_client.models.generate_content.return_value = mock_response
    
    agent_a = instantiate_temporal_agent(20, 2000)
    agent_b = instantiate_temporal_agent(40, 1980)
    
    conversation = await simulate_dialectic(agent_a, agent_b, "Technology impact")
    
    assert isinstance(conversation, list)
    assert len(conversation) > 0
    assert all(isinstance(msg, str) for msg in conversation)
    
    full_text = " ".join(conversation)
    assert str(agent_a.age) in full_text
    assert str(agent_b.age) in full_text

def test_duplicate_age_agents():
    """TRACE-TRAG-005: Test identical ages produce identical filters."""
    logger.debug("Testing duplicate age agents")
    
    agent1 = instantiate_temporal_agent(25, 1995)
    agent2 = instantiate_temporal_agent(25, 1995)
    
    assert agent1.memory_filter == agent2.memory_filter
