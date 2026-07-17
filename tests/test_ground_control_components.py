import sys
from unittest.mock import MagicMock

# Mock chainlit
cl_mock = MagicMock()
sys.modules['chainlit'] = cl_mock

from singularity.core.agent_base import (
    AgentStatus,
    AsyncBaseAgent,
    InterruptRequest,
    ProposedAction,
    RiskLevel,
)
from singularity.ground_control.components import (
    build_sync_prompt_card,
    build_constellation_overview,
    build_heartbeat_indicator,
    build_welcome_message,
)

def test_build_sync_prompt_card():
    action = ProposedAction(
        action_id="act-123",
        action_type="db_write",
        agent_id="test-agent",
        description="Write some data",
        risk_level=RiskLevel.MEDIUM,
        parameters={"foo": "bar"}
    )
    interrupt = InterruptRequest(proposed_action=action)
    
    msg = build_sync_prompt_card(interrupt)
    
    cl_mock.Message.assert_called_once()
    kwargs = cl_mock.Message.call_args[1]
    content = kwargs["content"]
    assert "act-123" in content
    assert "db_write" in content
    assert "MEDIUM" in content
    assert "foo" in content
    assert "bar" in content
    assert "actions" in kwargs
    
    cl_mock.Message.reset_mock()
    
    # test without parameters
    action.parameters = None
    msg = build_sync_prompt_card(InterruptRequest(proposed_action=action))
    assert "foo" not in cl_mock.Message.call_args[1]["content"]
    cl_mock.Message.reset_mock()
    
    # test unknown risk (fallback)
    action.risk_level = MagicMock() # not a RiskLevel enum
    action.risk_level.value = "unknown"
    msg = build_sync_prompt_card(InterruptRequest(proposed_action=action))
    assert "UNKNOWN" in cl_mock.Message.call_args[1]["content"]

def test_build_constellation_overview():
    agent1 = MagicMock()
    agent1.status = AgentStatus.NOMINAL
    agent1.agent_name = "Agent 1"
    agent1.agent_id = "a1"
    agent1.agent_role = "role1"
    agent1.priority = 1
    
    agent2 = MagicMock()
    agent2.status = AgentStatus.ERROR
    agent2.agent_name = "Agent 2"
    agent2.agent_id = "a2"
    agent2.agent_role = "role2"
    agent2.priority = 2
    
    agent3 = MagicMock()
    mock_status = MagicMock()
    mock_status.value = "FAKE_STATUS"
    agent3.status = mock_status  # to test the fallback emoji
    
    overview = build_constellation_overview([agent1, agent2, agent3])
    
    assert "Agent 1" in overview
    assert "Agent 2" in overview
    assert "nominal" in overview
    assert "error" in overview
    assert "⚪" in overview  # fallback emoji

def test_build_heartbeat_indicator():
    res = build_heartbeat_indicator(0)
    assert "NOW" in res
    
    res = build_heartbeat_indicator(5)
    assert "🟡" in res
    assert "5s" in res
    
    res = build_heartbeat_indicator(15)
    assert "🟢" in res
    assert "15s" in res

def test_build_welcome_message():
    res = build_welcome_message()
    assert "Simulated Singularity" in res
