"""Evolutionary RLHF Topology Optimizer for the N-Dimensional Swarm Graph."""

import random
import logging
from singularity.orchestration.swarm_state import SwarmState

logger = logging.getLogger(__name__)

ALPHA = 0.1  # Learning rate
DECAY_FACTOR = 0.99  # Synaptic pruning decay
EPSILON_PROB = 0.1  # Probability of genetic exploration
MIN_WEIGHT = 0.01
MAX_WEIGHT = 1.0

def mutate_topology(state: SwarmState, feedback_reward: float, source: str, target: str) -> SwarmState:
    """Mutate the swarm adjacency matrix based on RLHF feedback."""
    logger.info(f"Mutating topology: reward={feedback_reward} source={source} target={target}")
    
    new_state = state.model_copy(deep=True)
    matrix = new_state.adjacency_matrix
    
    # Ensure source and target exist in matrix
    if source not in matrix:
        matrix[source] = {}
    if target not in matrix[source]:
        matrix[source][target] = 0.5  # default initial weight
        
    # Q-learning update: W = W + alpha * (R - W)
    current_w = matrix[source][target]
    updated_w = current_w + ALPHA * (feedback_reward - current_w)
    matrix[source][target] = updated_w
    
    # Apply decay and bounds to all edges, occasionally add epsilon
    for s_node in list(matrix.keys()):
        for t_node in list(matrix[s_node].keys()):
            w = matrix[s_node][t_node]
            # Decay
            w *= DECAY_FACTOR
            
            # Genetic exploration
            if random.random() < EPSILON_PROB:
                epsilon = random.uniform(-0.05, 0.05)
                w += epsilon
                
            # Bounds
            w = max(MIN_WEIGHT, min(MAX_WEIGHT, w))
            matrix[s_node][t_node] = w
            
    new_state.adjacency_matrix = matrix
    return new_state
