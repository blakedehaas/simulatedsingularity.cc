"""Hive Mind Social Dynamics Engine for the N-Dimensional Swarm Graph."""

import logging
from typing import Any
from singularity.swarm_orchestration.swarm_state import SwarmState

logger = logging.getLogger(__name__)

def detect_clusters(state: SwarmState) -> list[set[str]]:
    """Find connected components in the adjacency matrix using edges >= 0.5."""
    matrix = state.adjacency_matrix
    nodes = set(state.active_agents)
    
    # Also include nodes present in the matrix
    for s_node in matrix.keys():
        nodes.add(s_node)
        for t_node in matrix[s_node].keys():
            nodes.add(t_node)
            
    visited = set()
    clusters = []
    
    # Build undirected adjacency for clustering purposes
    adj = {n: set() for n in nodes}
    for s_node, targets in matrix.items():
        for t_node, w in targets.items():
            if w >= 0.5:
                if t_node in adj:
                    adj[s_node].add(t_node)
                    adj[t_node].add(s_node)
                
    for node in nodes:
        if node not in visited:
            # BFS or DFS to find connected component
            component = set()
            queue = [node]
            while queue:
                current = queue.pop(0)
                if current not in visited:
                    visited.add(current)
                    component.add(current)
                    queue.extend(list(adj[current]))
            clusters.append(component)
            
    logger.debug(f"Detected {len(clusters)} clusters")
    return clusters

def assign_hierarchy(state: SwarmState, clusters: list[set[str]]) -> list[str]:
    """Calculate in-degree centrality per cluster to designate leaders."""
    leaders = []
    matrix = state.adjacency_matrix
    
    for cluster in clusters:
        if not cluster:
            continue
            
        in_degrees = {n: 0.0 for n in cluster}
        for s_node in cluster:
            if s_node in matrix:
                for t_node in cluster:
                    if t_node in matrix[s_node]:
                        in_degrees[t_node] += matrix[s_node][t_node]
                        
        # Find node with highest in-degree
        leader = max(in_degrees.items(), key=lambda x: x[1])[0]
        leaders.append(leader)
        
    logger.debug(f"Assigned leaders: {leaders}")
    return leaders
