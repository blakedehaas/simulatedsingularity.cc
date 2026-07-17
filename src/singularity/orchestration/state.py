"""LangGraph state schema for the Simulated Singularity constellation.

Defines :class:`ConstellationState` — the central TypedDict that flows
through every node in the orchestration graph.  LangGraph uses type
annotations (via ``Annotated``) to determine how individual fields are
*reduced* when parallel branches or successive nodes return partial
updates.

Key design decisions
--------------------
* ``messages`` uses the built-in ``add_messages`` reducer so that each
  node can *append* messages without replacing the full list.
* ``proposed_actions`` and ``pending_interrupts`` use a custom list-
  append reducer so actions accumulate across multiple agent hops.
* Scalar fields (``current_agent``, ``heartbeat_sequence``,
  ``is_interrupted``) use a simple "last-write-wins" reducer.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from singularity.core.agent_base import (
    InterruptRequest,
    ProposedAction,
    TelemetryFrame,
)


# ---------------------------------------------------------------------------
# Custom reducers
# ---------------------------------------------------------------------------

def _append_list(existing: list[Any], update: list[Any]) -> list[Any]:
    """Reducer that appends *update* items onto *existing*.

    Used for accumulating proposed actions and pending interrupts across
    successive graph nodes without overwriting earlier entries.

    Args:
        existing: The current list stored in the state channel.
        update: New items returned by the latest node.

    Returns:
        A new list containing all existing items followed by the update
        items.
    """
    return existing + update


def _merge_telemetry(
    existing: dict[str, TelemetryFrame],
    update: dict[str, TelemetryFrame],
) -> dict[str, TelemetryFrame]:
    """Reducer that merges telemetry frames by agent ID.

    Later frames for the same agent overwrite earlier ones.

    Args:
        existing: Current telemetry frame mapping.
        update: New telemetry frames returned by the latest node.

    Returns:
        A merged dictionary of telemetry frames keyed by agent ID.
    """
    merged = dict(existing)
    merged.update(update)
    return merged


# ---------------------------------------------------------------------------
# Constellation state definition
# ---------------------------------------------------------------------------

class ConstellationState:
    """LangGraph state schema for the Simulated Singularity graph.

    This class is used as a **TypedDict-style** schema via
    ``StateGraph(ConstellationState)``.  Each field carries an
    ``Annotated`` type that tells LangGraph how to *reduce* partial
    updates from individual nodes into the shared state.

    Attributes:
        messages: Conversation message history.  Uses LangGraph's
            built-in ``add_messages`` reducer to append new messages
            while deduplicating by ID.
        current_agent: ID of the agent currently being executed (or
            about to be executed).  Last-write-wins.
        routing_history: Ordered list of agent IDs visited during this
            graph invocation.  Appended via list concatenation.
        proposed_actions: Actions proposed by agents that may require
            C2 approval.  Accumulated across nodes.
        pending_interrupts: Interrupt requests that have not yet been
            resolved.  Accumulated across nodes.
        telemetry_frames: Latest telemetry snapshot per agent.  Merged
            by agent ID so newer frames overwrite older ones.
        heartbeat_sequence: Monotonically increasing heartbeat counter
            from the Mission Scheduler.  Last-write-wins.
        is_interrupted: ``True`` when the graph is paused awaiting C2
            operator resolution of an interrupt.  Last-write-wins.
    """

    # We declare the schema as class-level annotations so that
    # ``StateGraph`` can introspect the fields and their reducers.
    __annotations__ = {
        "messages": Annotated[list[BaseMessage], add_messages],
        "current_agent": str,
        "routing_history": Annotated[list[str], operator.add],
        "proposed_actions": Annotated[list[ProposedAction], _append_list],
        "pending_interrupts": Annotated[list[InterruptRequest], _append_list],
        "telemetry_frames": Annotated[dict[str, TelemetryFrame], _merge_telemetry],
        "heartbeat_sequence": int,
        "is_interrupted": bool,
    }


# Re-export annotations at module level for external introspection.
messages: Annotated[list[BaseMessage], add_messages]
current_agent: str
routing_history: Annotated[list[str], operator.add]
proposed_actions: Annotated[list[ProposedAction], _append_list]
pending_interrupts: Annotated[list[InterruptRequest], _append_list]
telemetry_frames: Annotated[dict[str, TelemetryFrame], _merge_telemetry]
heartbeat_sequence: int
is_interrupted: bool
