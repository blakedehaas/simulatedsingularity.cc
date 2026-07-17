"""Concrete agent implementations for the orbital constellation."""

from singularity.agents.analytical_agent import AnalyticalAgent
from singularity.agents.coding_agent import CodingAgent
from singularity.agents.core_agent import CoreAgent
from singularity.agents.creative_agent import CreativeAgent
from singularity.agents.environment_agent import EnvironmentAgent
from singularity.agents.memory_agent import MemoryAgent
from singularity.agents.prompt_agent import PromptAgent
from singularity.agents.security_agent import SecurityAgent

__all__ = [
    "AnalyticalAgent",
    "CodingAgent",
    "CoreAgent",
    "CreativeAgent",
    "EnvironmentAgent",
    "MemoryAgent",
    "PromptAgent",
    "SecurityAgent",
]
