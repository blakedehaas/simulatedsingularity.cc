"""Pydantic models for the N-Dimensional Swarm Graph state."""

from typing import Any
from pydantic import BaseModel, Field

class SwarmState(BaseModel):
    """State object for the dynamic swarm routing graph.
    
    Attributes:
        messages: Conversation history.
        active_agents: List of active agent IDs currently participating in the swarm.
        adjacency_matrix: N x N matrix tracking connection weights (affinity) between agents.
            Stored as a dictionary of dictionaries, e.g., {"agent_a": {"agent_b": 0.8}}.
    """
    messages: list[Any] = Field(default_factory=list)
    active_agents: list[str] = Field(default_factory=list)
    adjacency_matrix: dict[str, dict[str, float]] = Field(default_factory=dict)
