"""Swarm Orchestration — state graphs, routing, evolutionary topology, and interrupt hooks.

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

from singularity.swarm_orchestration.state import ConstellationState, TriadicState
from singularity.swarm_orchestration.interrupts import InterruptHandler

# Lazy imports for graph modules that depend on optional langgraph checkpoint packages.
def __getattr__(name):
    if name in ("build_graph", "resume_after_interrupt", "run_prompt"):
        from singularity.swarm_orchestration.graph import build_graph, resume_after_interrupt, run_prompt
        return {"build_graph": build_graph, "resume_after_interrupt": resume_after_interrupt, "run_prompt": run_prompt}[name]
    if name in ("build_triadic_graph", "run_triadic_prompt", "resume_triadic_interrupt"):
        from singularity.swarm_orchestration.triadic_graph import build_triadic_graph, run_triadic_prompt, resume_triadic_interrupt
        return {"build_triadic_graph": build_triadic_graph, "run_triadic_prompt": run_triadic_prompt, "resume_triadic_interrupt": resume_triadic_interrupt}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

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

