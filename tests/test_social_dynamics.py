import pytest
from singularity.orchestration.swarm_state import SwarmState
from singularity.orchestration.social_dynamics import detect_clusters, assign_hierarchy

def test_detect_clusters():
    """Test finding connected components with weight >= 0.5."""
    state = SwarmState(
        messages=[],
        active_agents=["a", "b", "c", "d"],
        adjacency_matrix={
            "a": {"b": 0.9},
            "b": {"a": 0.8},
            "c": {"d": 0.6}
        }
    )
    
    clusters = detect_clusters(state)
    assert len(clusters) == 2
    
    cluster_sets = [set(c) for c in clusters]
    assert {"a", "b"} in cluster_sets
    assert {"c", "d"} in cluster_sets

def test_assign_hierarchy():
    """Test calculating in-degree centrality to find a leader."""
    state = SwarmState(
        messages=[],
        active_agents=["leader_node", "sub1", "sub2"],
        adjacency_matrix={
            "sub1": {"leader_node": 1.0},
            "sub2": {"leader_node": 0.8, "sub1": 0.1},
            "leader_node": {"sub1": 0.1}
        }
    )
    
    # Passing them as a single cluster
    clusters = [{"leader_node", "sub1", "sub2"}]
    leaders = assign_hierarchy(state, clusters)
    
    # leader_node has 1.8 incoming weight, sub1 has 0.2, sub2 has 0
    assert len(leaders) == 1
    assert leaders[0] == "leader_node"
