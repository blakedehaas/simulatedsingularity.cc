"""N-Dimensional Swarm Graph using LangGraph's Send API."""

import logging
from typing import Any
from langgraph.graph import StateGraph, START
from langgraph.constants import Send

from singularity.orchestration.swarm_state import SwarmState

logger = logging.getLogger(__name__)

# Weight threshold above which we dispatch states to connected agents
WEIGHT_THRESHOLD = 0.5

def topology_router(state: SwarmState) -> list[Send]:
    """Evaluates the adjacency matrix and uses LangGraph's Send API to dispatch to multiple agents."""
    sends = []
    
    logger.debug("Evaluating topology for routing...")
    
    # We conditionally dispatch to all active agents that have high affinity.
    for source, targets in state.adjacency_matrix.items():
        for target, weight in targets.items():
            if weight >= WEIGHT_THRESHOLD and target in state.active_agents:
                # Dispatching state to the target agent node
                logger.info(f"Routing to {target} due to weight {weight} from {source}")
                sends.append(Send(target, state))
                
    if not sends and state.active_agents:
        # Fallback to the first active agent if no strong connections exist
        fallback = state.active_agents[0]
        sends.append(Send(fallback, state))
        
    return sends

def create_swarm_graph(agent_nodes: dict[str, Any]) -> Any:
    """Build the dynamic StateGraph.
    
    Args:
        agent_nodes: Dictionary mapping agent_id to their node functions.
    """
    builder = StateGraph(SwarmState)
    
    # Add a router node that just returns the state as is, 
    # to act as a hub before conditionally routing
    builder.add_node("router", lambda state: state)
    
    # Add agent nodes
    for agent_id, node_func in agent_nodes.items():
        builder.add_node(agent_id, node_func)
        
    # The TopologyRouter determines where to send the state next
    builder.add_conditional_edges("router", topology_router)
    
    # After an agent acts, it loops back to the router
    for agent_id in agent_nodes.keys():
        builder.add_edge(agent_id, "router")
        
    builder.add_edge(START, "router")
    
    return builder.compile()
