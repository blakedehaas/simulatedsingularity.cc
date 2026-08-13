"""LangGraph orchestration — state graph, routing, and interrupt hooks.

Public API
----------
* :class:`ConstellationState` — TypedDict state schema for the graph.
* :func:`build_graph` — Construct and compile the state graph.
* :func:`run_prompt` — Invoke the graph with a user message.
* :func:`resume_after_interrupt` — Resume after C2 operator decision.
* :class:`InterruptHandler` — Interrupt lifecycle management.
* :class:`TriadicState` — TypedDict state schema for the triadic graph.
* :func:`build_triadic_graph` — Construct and compile the triadic state graph.
* :func:`run_triadic_prompt` — Invoke the triadic graph with a user message.
* :func:`resume_triadic_interrupt` — Resume the triadic graph after C2 decision.
"""

from singularity.orchestration.state import ConstellationState, TriadicState
from singularity.orchestration.graph import (
    build_graph,
    resume_after_interrupt,
    run_prompt,
)
from singularity.orchestration.triadic_graph import (
    build_triadic_graph,
    run_triadic_prompt,
    resume_triadic_interrupt,
)
from singularity.orchestration.interrupts import InterruptHandler

__all__ = [
    "ConstellationState",
    "TriadicState",
    "InterruptHandler",
    "build_graph",
    "resume_after_interrupt",
    "run_prompt",
    "build_triadic_graph",
    "run_triadic_prompt",
    "resume_triadic_interrupt",
]
