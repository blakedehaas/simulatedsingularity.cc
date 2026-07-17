"""LangGraph orchestration — state graph, routing, and interrupt hooks.

Public API
----------
* :class:`ConstellationState` — TypedDict state schema for the graph.
* :func:`build_graph` — Construct and compile the state graph.
* :func:`run_prompt` — Invoke the graph with a user message.
* :func:`resume_after_interrupt` — Resume after C2 operator decision.
* :class:`InterruptHandler` — Interrupt lifecycle management.
"""

from singularity.orchestration.state import ConstellationState
from singularity.orchestration.graph import (
    build_graph,
    resume_after_interrupt,
    run_prompt,
)
from singularity.orchestration.interrupts import InterruptHandler

__all__ = [
    "ConstellationState",
    "InterruptHandler",
    "build_graph",
    "resume_after_interrupt",
    "run_prompt",
]
