"""Agent registry for discovery, instantiation, and lifecycle management.

Provides a centralized registry where agent classes are registered via
decorator and can be looked up by ID. Handles constellation initialization
and ordered iteration by agent priority.
"""

from __future__ import annotations

import logging
from typing import Any

from singularity.neural_core.node_base import NodeStatus, CognitiveNode

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global registry storage
# ---------------------------------------------------------------------------

_AGENT_CLASSES: dict[str, type[CognitiveNode]] = {}
_AGENT_INSTANCES: dict[str, CognitiveNode] = {}


# ---------------------------------------------------------------------------
# Registration decorator
# ---------------------------------------------------------------------------

def register_agent(cls: type[CognitiveNode]) -> type[CognitiveNode]:
    """Class decorator that registers an agent class in the global registry.

    The agent class must define a class-level ``AGENT_ID`` attribute that
    serves as the registry key.

    Example::

        @register_agent
        class FirewallNode(CognitiveNode):
            AGENT_ID = "security-001"
            ...

    Args:
        cls: The agent class to register.

    Returns:
        The same class, unmodified.

    Raises:
        ValueError: If ``AGENT_ID`` is not defined or already registered.
    """
    node_id = getattr(cls, "AGENT_ID", None)
    if node_id is None:
        raise ValueError(
            f"Agent class {cls.__name__} must define a class-level AGENT_ID attribute."
        )
    if node_id in _AGENT_CLASSES:
        raise ValueError(
            f"Agent ID {node_id!r} is already registered by {_AGENT_CLASSES[node_id].__name__}."
        )
    _AGENT_CLASSES[node_id] = cls
    logger.info("Registered agent class %s with ID %r", cls.__name__, node_id)
    return cls


# ---------------------------------------------------------------------------
# Registry operations
# ---------------------------------------------------------------------------

def get_agent(node_id: str) -> CognitiveNode:
    """Retrieve a running agent instance by its ID.

    Args:
        node_id: The unique identifier of the agent.

    Returns:
        The agent instance.

    Raises:
        KeyError: If no agent with the given ID has been instantiated.
    """
    if node_id not in _AGENT_INSTANCES:
        raise KeyError(f"No running agent instance with ID {node_id!r}.")
    return _AGENT_INSTANCES[node_id]


def get_all_agents() -> list[CognitiveNode]:
    """Return all running agent instances ordered by priority (ascending).

    Returns:
        A list of agent instances sorted by ``priority`` (lower = higher
        priority).
    """
    return sorted(_AGENT_INSTANCES.values(), key=lambda a: a.priority)


def get_registered_classes() -> dict[str, type[CognitiveNode]]:
    """Return a copy of the registered agent class mapping.

    Returns:
        Dictionary mapping agent IDs to their classes.
    """
    return dict(_AGENT_CLASSES)


def initialize_constellation(**kwargs: Any) -> list[CognitiveNode]:
    """Instantiate all registered agent classes and activate them.

    Creates an instance of every registered agent class, sets each to
    :attr:`NodeStatus.NOMINAL`, and stores them in the instance registry.

    Args:
        **kwargs: Additional keyword arguments forwarded to each agent's
            ``__init__`` method.

    Returns:
        A list of all instantiated agents, ordered by priority.
    """
    _AGENT_INSTANCES.clear()

    for node_id, agent_cls in _AGENT_CLASSES.items():
        try:
            instance = agent_cls(**kwargs)
            instance.set_status(NodeStatus.NOMINAL)
            _AGENT_INSTANCES[node_id] = instance
            logger.info(
                "Initialized agent %s (%s) — priority %d",
                instance.node_name,
                node_id,
                instance.priority,
            )
        except Exception:
            logger.exception("Failed to initialize agent class %s", agent_cls.__name__)
            raise

    agents = get_all_agents()
    logger.info(
        "Constellation initialized: %d agents active",
        len(agents),
    )
    return agents


def reset_registry() -> None:
    """Clear all registered classes and running instances.

    Primarily used for testing to reset global state between test runs.
    """
    _AGENT_CLASSES.clear()
    _AGENT_INSTANCES.clear()
