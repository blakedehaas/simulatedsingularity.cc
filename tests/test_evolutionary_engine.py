import pytest
from singularity.swarm_orchestration.swarm_state import SwarmState
from singularity.swarm_orchestration.evolutionary_engine import mutate_topology, MIN_WEIGHT, MAX_WEIGHT
from langchain_core.messages import AIMessage

def test_mutate_topology_bounds():
    """Test that the Q-learning math bounds weights strictly between [0.01, 1.0]."""
    # Setup mock state with extreme weights to test bounding
    state = SwarmState(
        messages=[],
        active_agents=["agent_a", "agent_b", "agent_c"],
        adjacency_matrix={
            "agent_a": {"agent_b": 0.0, "agent_c": 1.5}
        }
    )
    
    # Mutate with a massive reward to push it high
    new_state = mutate_topology(state, feedback_reward=100.0, source="agent_a", target="agent_b")
    
    matrix = new_state.adjacency_matrix
    assert matrix["agent_a"]["agent_b"] <= MAX_WEIGHT
    assert matrix["agent_a"]["agent_b"] >= MIN_WEIGHT
    
    assert matrix["agent_a"]["agent_c"] <= MAX_WEIGHT
    assert matrix["agent_a"]["agent_c"] >= MIN_WEIGHT

def test_mutate_topology_new_edge():
    """Test creating a new edge during mutation."""
    state = SwarmState(
        messages=[],
        active_agents=["agent_a", "agent_b"],
        adjacency_matrix={}
    )
    
    new_state = mutate_topology(state, feedback_reward=0.8, source="agent_a", target="agent_b")
    matrix = new_state.adjacency_matrix
    
    assert "agent_a" in matrix
    assert "agent_b" in matrix["agent_a"]
    # Starting weight is 0.5, with reward 0.8 and alpha 0.1, new is 0.5 + 0.1*(0.8-0.5) = 0.53
    # Then decay 0.99 = ~0.5247 (ignoring epsilon for deterministic test approximations, 
    # but epsilon can shift this slightly. We just assert it exists and is bounded.)
    w = matrix["agent_a"]["agent_b"]
    assert MIN_WEIGHT <= w <= MAX_WEIGHT
