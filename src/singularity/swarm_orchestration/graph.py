"""LangGraph state-graph definition for the Simulated Singularity C2 system.

Builds a :class:`~langgraph.graph.StateGraph` whose nodes mirror the
constellation's agent architecture:

1. **security_check** — The Security Agent always runs first as a
   priority gate, scanning every inbound payload for threats.
2. **core_router** — The Core Agent inspects payload metadata and
   determines which functional agent should process the request.
3. **agent_executor** — Invokes the target functional agent identified
   by the core router.
4. **prompt_relay** — The Prompt Relay Agent aggregates and logs
   communications and telemetry.
5. **telemetry_emit** — Emits a consolidated telemetry frame before
   the graph terminates.

The graph uses LangGraph's ``interrupt()`` mechanism to pause execution
whenever a state-mutating action is proposed, giving the C2 operator a
chance to approve, deny, or modify the action before it takes effect.

Public API
----------
* :func:`build_graph` — Construct and compile the state graph.
* :func:`run_prompt` — Invoke the compiled graph with a user message.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from singularity.neural_core.node_base import (
    CognitiveOutput,
    NodeStatus,
    C2InterventionRequest,
    InterruptResolution,
    ActionProposal,
    SynapticTransmission,
    RiskLevel,
    DiagnosticFrame,
)
from singularity.neural_core.node_registry import get_agent, get_all_agents
from singularity.swarm_orchestration.state import ConstellationState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Well-known agent IDs used by the graph
# ---------------------------------------------------------------------------

_SECURITY_AGENT_ID = "security-001"
_CORE_AGENT_ID = "core-001"
_PROMPT_RELAY_AGENT_ID = "prompt-001"

# Risk levels that trigger an interrupt for C2 review
_INTERRUPT_RISK_THRESHOLD: set[RiskLevel] = {RiskLevel.HIGH, RiskLevel.CRITICAL}


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------

async def security_check(state: dict[str, Any]) -> dict[str, Any]:
    """Priority gate — the Security Agent scans every inbound payload.

    If the security agent is not registered the node passes through
    without modification (graceful degradation).

    Args:
        state: The current constellation state dictionary.

    Returns:
        State update with the security agent's response appended as an
        :class:`AIMessage` and routing history updated.
    """
    logger.info("🛡️  Security gate — scanning payload")

    try:
        agent = get_agent(_SECURITY_AGENT_ID)
    except KeyError:
        logger.warning(
            "Security agent %r not found — skipping security gate",
            _SECURITY_AGENT_ID,
        )
        return {
            "routing_history": [_SECURITY_AGENT_ID + ":skipped"],
        }

    # Build a payload from the last human message
    last_human = _extract_last_human_text(state.get("messages", []))
    payload = SynapticTransmission(
        source_node_id="ground_control",
        target_node_id=_SECURITY_AGENT_ID,
        content=last_human,
    )

    response: CognitiveOutput = await agent.receive_prompt(payload)

    return {
        "messages": [AIMessage(content=response.content, name=_SECURITY_AGENT_ID)],
        "current_agent": _SECURITY_AGENT_ID,
        "routing_history": [_SECURITY_AGENT_ID],
        "telemetry_frames": {_SECURITY_AGENT_ID: response.telemetry},
    }


async def core_router(state: dict[str, Any]) -> dict[str, Any]:
    """Route the payload to the appropriate functional agent.

    The Core Agent examines payload metadata and returns a response
    whose ``metadata["route_to"]`` value indicates the next agent.
    If no explicit route is provided, the payload stays with core.

    Args:
        state: The current constellation state dictionary.

    Returns:
        State update setting ``current_agent`` to the routed target.
    """
    logger.info("⚙️  Core router — determining target agent")

    try:
        agent = get_agent(_CORE_AGENT_ID)
    except KeyError:
        logger.warning(
            "Core agent %r not found — terminating route",
            _CORE_AGENT_ID,
        )
        return {
            "current_agent": _CORE_AGENT_ID,
            "routing_history": [_CORE_AGENT_ID + ":missing"],
        }

    last_human = _extract_last_human_text(state.get("messages", []))
    payload = SynapticTransmission(
        source_node_id=_SECURITY_AGENT_ID,
        target_node_id=_CORE_AGENT_ID,
        content=last_human,
    )

    response: CognitiveOutput = await agent.receive_prompt(payload)

    # Determine routing target from response metadata
    route_target: str = response.metadata.get("route_to", _CORE_AGENT_ID)

    return {
        "messages": [AIMessage(content=response.content, name=_CORE_AGENT_ID)],
        "current_agent": route_target,
        "routing_history": [_CORE_AGENT_ID],
        "telemetry_frames": {_CORE_AGENT_ID: response.telemetry},
    }


async def agent_executor(state: dict[str, Any]) -> dict[str, Any]:
    """Execute the functional agent selected by the core router.

    If the target agent proposes any HIGH or CRITICAL risk actions,
    this node fires a LangGraph ``interrupt()`` to pause execution
    until the C2 operator resolves the action.

    Args:
        state: The current constellation state dictionary.

    Returns:
        State update with the agent's response, proposed actions,
        and any interrupt requests generated.
    """
    target_id: str = state.get("current_agent", _CORE_AGENT_ID)
    logger.info("🚀 Agent executor — invoking %r", target_id)

    try:
        agent = get_agent(target_id)
    except KeyError:
        logger.error("Target agent %r not found in registry", target_id)
        error_msg = f"Agent {target_id!r} is not registered in the constellation."
        return {
            "messages": [AIMessage(content=error_msg, name="system")],
            "routing_history": [target_id + ":not_found"],
        }

    last_human = _extract_last_human_text(state.get("messages", []))
    payload = SynapticTransmission(
        source_node_id=_CORE_AGENT_ID,
        target_node_id=target_id,
        content=last_human,
    )

    response: CognitiveOutput = await agent.receive_prompt(payload)

    # Check for high-risk proposed actions → trigger interrupt
    new_interrupts: list[C2InterventionRequest] = []
    for action in response.proposed_actions:
        if action.risk_level in _INTERRUPT_RISK_THRESHOLD:
            logger.warning(
                "⚠️  HIGH-RISK action proposed by %r: %s (risk=%s)",
                target_id,
                action.description,
                action.risk_level.value,
            )
            # Build the interrupt request
            irq = C2InterventionRequest(
                proposed_action=action,
                serialized_state={
                    "node_id": target_id,
                    "action_id": action.action_id,
                    "routing_history": state.get("routing_history", []),
                    "heartbeat_seq": state.get("heartbeat_sequence", 0),
                },
            )
            new_interrupts.append(irq)

            # Pause graph execution — LangGraph will persist state and
            # resume when the C2 operator supplies a resolution via
            # ``Command(resume=...)``.
            resolution = interrupt(
                {
                    "interrupt_id": irq.interrupt_id,
                    "action_id": action.action_id,
                    "node_id": target_id,
                    "action_type": action.action_type,
                    "description": action.description,
                    "risk_level": action.risk_level.value,
                    "parameters": action.parameters,
                }
            )

            # Process the C2 operator's resolution
            logger.info(
                "📋 Interrupt %s resolved: %s",
                irq.interrupt_id,
                resolution,
            )
            irq.resolution = InterruptResolution(
                resolution.get("decision", "approved")
                if isinstance(resolution, dict)
                else str(resolution)
            )

    return {
        "messages": [AIMessage(content=response.content, name=target_id)],
        "current_agent": target_id,
        "routing_history": [target_id],
        "proposed_actions": response.proposed_actions,
        "pending_interrupts": new_interrupts,
        "telemetry_frames": {target_id: response.telemetry},
        "is_interrupted": len(new_interrupts) > 0,
    }


async def prompt_relay(state: dict[str, Any]) -> dict[str, Any]:
    """Aggregate communications and relay telemetry through the Prompt Agent.

    If the prompt relay agent is not registered the node produces a
    summary message from the accumulated state.

    Args:
        state: The current constellation state dictionary.

    Returns:
        State update with a relay summary message.
    """
    logger.info("📡 Prompt relay — aggregating communications")

    try:
        agent = get_agent(_PROMPT_RELAY_AGENT_ID)
    except KeyError:
        # Graceful degradation — synthesize a summary
        visited = state.get("routing_history", [])
        summary = (
            f"Prompt relay complete. Routing path: {' → '.join(visited)}. "
            f"Telemetry frames collected: {len(state.get('telemetry_frames', {}))}."
        )
        return {
            "messages": [AIMessage(content=summary, name="prompt_relay")],
            "routing_history": [_PROMPT_RELAY_AGENT_ID + ":synthetic"],
        }

    last_human = _extract_last_human_text(state.get("messages", []))
    payload = SynapticTransmission(
        source_node_id=state.get("current_agent", "system"),
        target_node_id=_PROMPT_RELAY_AGENT_ID,
        content=last_human,
        metadata={
            "routing_history": state.get("routing_history", []),
            "action_count": len(state.get("proposed_actions", [])),
        },
    )

    response: CognitiveOutput = await agent.receive_prompt(payload)

    return {
        "messages": [AIMessage(content=response.content, name=_PROMPT_RELAY_AGENT_ID)],
        "routing_history": [_PROMPT_RELAY_AGENT_ID],
        "telemetry_frames": {_PROMPT_RELAY_AGENT_ID: response.telemetry},
    }


async def telemetry_emit(state: dict[str, Any]) -> dict[str, Any]:
    """Emit a consolidated telemetry report as the final graph node.

    Collects telemetry from all agents that participated in this
    invocation and produces a summary message.

    Args:
        state: The current constellation state dictionary.

    Returns:
        State update with a telemetry summary message and incremented
        heartbeat sequence.
    """
    logger.info("📊 Telemetry emit — final constellation snapshot")

    frames: dict[str, DiagnosticFrame] = state.get("telemetry_frames", {})
    agent_summaries: list[str] = []
    for node_id, frame in frames.items():
        agent_summaries.append(
            f"  • {node_id}: status={frame.status.value}, "
            f"metrics={frame.metrics}"
        )

    summary_text = (
        "📊 TELEMETRY REPORT\n"
        + "\n".join(agent_summaries or ["  (no telemetry frames collected)"])
        + f"\n  Heartbeat seq: {state.get('heartbeat_sequence', 0)}"
        + f"\n  Routing path: {' → '.join(state.get('routing_history', []))}"
    )

    return {
        "messages": [AIMessage(content=summary_text, name="telemetry")],
        "heartbeat_sequence": state.get("heartbeat_sequence", 0) + 1,
    }


# ---------------------------------------------------------------------------
# Conditional routing helpers
# ---------------------------------------------------------------------------

def _route_after_core(state: dict[str, Any]) -> str:
    """Decide whether to run agent_executor or skip to prompt_relay.

    If the core router set ``current_agent`` to itself (no delegation),
    we skip straight to the prompt relay.

    Args:
        state: The current constellation state dictionary.

    Returns:
        Name of the next node: ``"agent_executor"`` or ``"prompt_relay"``.
    """
    target = state.get("current_agent", _CORE_AGENT_ID)
    if target == _CORE_AGENT_ID:
        logger.info("Core router did not delegate — skipping to prompt relay")
        return "prompt_relay"
    return "agent_executor"


def _route_after_executor(state: dict[str, Any]) -> str:
    """Decide the next node after agent execution.

    Always proceeds to the prompt relay.

    Args:
        state: The current constellation state dictionary.

    Returns:
        ``"prompt_relay"``.
    """
    return "prompt_relay"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph(
    checkpoint_path: str | Path = "checkpoints.sqlite",
) -> tuple[Any, AsyncSqliteSaver]:
    """Build and compile the Simulated Singularity state graph.

    The compiled graph uses :class:`AsyncSqliteSaver` for durable
    checkpointing so that interrupted executions can be resumed after
    C2 operator decisions.

    Args:
        checkpoint_path: File path for the SQLite checkpoint database.
            Defaults to ``"checkpoints.sqlite"`` in the working directory.

    Returns:
        A tuple of ``(compiled_graph, checkpointer)`` so the caller
        can manage the checkpointer lifecycle (``async with``).
    """
    graph = StateGraph(ConstellationState)

    # Register nodes
    graph.add_node("security_check", security_check)
    graph.add_node("core_router", core_router)
    graph.add_node("agent_executor", agent_executor)
    graph.add_node("prompt_relay", prompt_relay)
    graph.add_node("telemetry_emit", telemetry_emit)

    # Edges — linear pipeline with conditional fan-out from core_router
    graph.add_edge(START, "security_check")
    graph.add_edge("security_check", "core_router")

    # Core router conditionally delegates to a functional agent
    graph.add_conditional_edges(
        "core_router",
        _route_after_core,
        {
            "agent_executor": "agent_executor",
            "prompt_relay": "prompt_relay",
        },
    )

    # After agent execution always go to prompt relay
    graph.add_edge("agent_executor", "prompt_relay")

    # After relay always go to telemetry
    graph.add_edge("prompt_relay", "telemetry_emit")

    # Telemetry is the terminal node
    graph.add_edge("telemetry_emit", END)

    # Build async checkpointer
    checkpointer = AsyncSqliteSaver.from_conn_string(str(checkpoint_path))

    compiled = graph.compile(checkpointer=checkpointer)

    logger.info(
        "State graph compiled with %d nodes, checkpointing to %s",
        5,
        checkpoint_path,
    )

    return compiled, checkpointer


# ---------------------------------------------------------------------------
# High-level invocation helper
# ---------------------------------------------------------------------------

async def run_prompt(
    compiled_graph: Any,
    user_message: str,
    *,
    thread_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Invoke the constellation graph with a user message.

    Constructs the initial state from the user's message and runs the
    compiled graph to completion (or until an interrupt is triggered).

    Args:
        compiled_graph: The compiled :class:`StateGraph` returned by
            :func:`build_graph`.
        user_message: The human operator's message text.
        thread_id: Optional thread identifier for conversation
            continuity.  If ``None`` a new UUID is generated.
        metadata: Optional metadata to attach to the invocation.

    Returns:
        The final state dictionary after graph execution completes.
    """
    if thread_id is None:
        thread_id = uuid.uuid4().hex[:16]

    initial_state: dict[str, Any] = {
        "messages": [HumanMessage(content=user_message)],
        "current_agent": "",
        "routing_history": [],
        "proposed_actions": [],
        "pending_interrupts": [],
        "telemetry_frames": {},
        "heartbeat_sequence": 0,
        "is_interrupted": False,
    }

    config: dict[str, Any] = {
        "configurable": {
            "thread_id": thread_id,
        },
    }
    if metadata:
        config["metadata"] = metadata

    logger.info(
        "Invoking constellation graph — thread=%s, message=%r",
        thread_id,
        user_message[:80],
    )

    result = await compiled_graph.ainvoke(initial_state, config=config)

    logger.info(
        "Graph execution complete — thread=%s, routing=%s",
        thread_id,
        result.get("routing_history", []),
    )

    return result


async def resume_after_interrupt(
    compiled_graph: Any,
    thread_id: str,
    resolution: dict[str, Any],
) -> dict[str, Any]:
    """Resume graph execution after a C2 operator resolves an interrupt.

    Uses LangGraph's ``Command(resume=...)`` mechanism to supply the
    operator's decision and continue from the interrupted checkpoint.

    Args:
        compiled_graph: The compiled state graph.
        thread_id: The thread that was interrupted.
        resolution: The operator's resolution payload (e.g.
            ``{"decision": "approved"}``).

    Returns:
        The final state dictionary after the graph resumes and
        completes.
    """
    config: dict[str, Any] = {
        "configurable": {
            "thread_id": thread_id,
        },
    }

    logger.info(
        "Resuming interrupted graph — thread=%s, resolution=%s",
        thread_id,
        resolution,
    )

    result = await compiled_graph.ainvoke(
        Command(resume=resolution),
        config=config,
    )

    logger.info(
        "Graph resumed and completed — thread=%s, routing=%s",
        thread_id,
        result.get("routing_history", []),
    )

    return result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _extract_last_human_text(messages: list[Any]) -> str:
    """Extract the text content of the last human message.

    Args:
        messages: List of LangChain message objects.

    Returns:
        The content string of the last :class:`HumanMessage`, or an
        empty string if none is found.
    """
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            content = msg.content
            return content if isinstance(content, str) else str(content)
    return ""
