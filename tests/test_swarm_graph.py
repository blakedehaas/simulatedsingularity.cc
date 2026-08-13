import pytest
from singularity.swarm_orchestration.swarm_state import SwarmState
from singularity.swarm_orchestration.swarm_graph import create_swarm_graph, topology_router
from singularity.neural_core.node_base import SynapticWeightFeedback
from langchain_core.messages import AIMessage
from langgraph.constants import Send

@pytest.mark.asyncio
async def test_topology_router_dispatch():
    """Test that the topology router correctly dispatches based on the adjacency matrix."""
    # Setup mock state
    state = SwarmState(
        messages=[AIMessage(content="Hello world")],
        active_nodes=["agent_a", "agent_b", "agent_c"],
        adjacency_matrix={
            "agent_a": {"agent_b": 0.9, "agent_c": 0.2},
            "agent_b": {"agent_c": 0.8}
        }
    )
    
    # Run the router. It should dispatch to all valid edges >= 0.5 (the default threshold in swarm_graph.py)
    # The valid edges here are agent_a->agent_b and agent_b->agent_c
    sends = topology_router(state)
    
    # Assertions
    assert len(sends) == 2
    
    # We should have one Send to agent_b and one to agent_c
    target_nodes = [send.node for send in sends]
    assert "agent_b" in target_nodes
    assert "agent_c" in target_nodes
