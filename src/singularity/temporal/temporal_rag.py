"""
temporal_rag.py — Temporal Vector Slicing for Chronological Consciousness Forking.

By partitioning the Vector Database chronologically, this module creates
Temporal Homunculi — agents restricted to knowledge from a specific time window.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TemporalAgentNode:
    """A node representing a temporal consciousness slice of a user.

    The agent's RAG retriever is mathematically barred from accessing
    any memories, knowledge, or vocabulary encoded after the cutoff date.

    Attributes:
        system_prompt: The LLM system prompt restricting temporal awareness.
        memory_filter: ChromaDB-compatible ``where`` filter for temporal slicing.
        age:           The age at which this consciousness was forked.
    """

    def __init__(self, system_prompt: str, memory_filter: dict[str, Any], age: int) -> None:
        self.system_prompt = system_prompt
        self.memory_filter = memory_filter
        self.age = age
        logger.debug("Created TemporalAgentNode for age %d", self.age)

    def query_past(self, user_query: str, vector_memory: Any) -> str:
        """Query the vector database restricted to this temporal slice.

        Parameters:
            user_query:    Natural-language query string.
            vector_memory: A VectorMemory instance (or mock) with ``retrieve_context``.

        Returns:
            A formatted string containing the age-restricted recalled context.
        """
        logger.info("Querying past (age %d) for: %s", self.age, user_query)

        context = vector_memory.retrieve_context(
            query=user_query,
            filter=self.memory_filter,
        )
        context_str = str(context) if context else "No memories available."

        return f"[Age {self.age} Recall] {context_str}"


def instantiate_temporal_agent(target_age: int, user_birth_year: int) -> TemporalAgentNode:
    """Create a temporal agent node locked to a specific chronological cutoff.

    Parameters:
        target_age:      The age at which to freeze consciousness.
        user_birth_year: The user's birth year for calculating the cutoff.

    Returns:
        A ``TemporalAgentNode`` restricted to pre-cutoff memories.
    """
    cutoff_year = user_birth_year + target_age
    memory_filter = {"cutoff_year": cutoff_year}
    system_prompt = (
        f"You are the user, frozen at age {target_age}. "
        f"You only know what you knew before {cutoff_year}. "
        f"Answer from that perspective."
    )

    logger.info(
        "Instantiating temporal agent at age %d (cutoff year %d)",
        target_age, cutoff_year,
    )
    return TemporalAgentNode(
        system_prompt=system_prompt,
        memory_filter=memory_filter,
        age=target_age,
    )


async def simulate_dialectic(
    agent_a: TemporalAgentNode,
    agent_b: TemporalAgentNode,
    topic: str,
) -> list[str]:
    """Generate a simulated dialectic between two temporal agents."""
    import os
    import asyncio
    from google import genai
    
    logger.info(
        "Simulating dialectic on '%s' between age %d and age %d",
        topic, agent_a.age, agent_b.age,
    )

    younger = agent_a if agent_a.age < agent_b.age else agent_b
    older = agent_a if agent_a.age >= agent_b.age else agent_b

    prompt = f"""Write a 4-line dialogue between a younger version of a person (Age {younger.age}) and their older self (Age {older.age}) discussing {topic}.
Format exactly as:
[Age {younger.age}]: <text>
[Age {older.age}]: <text>
[Age {younger.age}]: <text>
[Age {older.age}]: <text>
Do not add extra formatting."""

    try:
        client = genai.Client()
        response = await asyncio.to_thread(
            client.models.generate_content,
            model='gemini-2.5-flash-8b',
            contents=prompt
        )
        lines = response.text.strip().split('\n')
        return [l.strip() for l in lines if l.strip()]
    except Exception as e:
        logger.error(f"Temporal RAG Error: {e}")
        return [f"[SYSTEM]: Error communicating with temporal matrix: {e}"]
