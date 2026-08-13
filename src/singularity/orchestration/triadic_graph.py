"""Triadic LangGraph state-graph definition for the Simulated Singularity C2 system.

Builds a StateGraph for the triadic orchestration pattern:
1. safeguard_screen - scans for threats
2. orchestrator_route - determines routing (synthesis or self_handle)
3. synthesis_execute - executes the synthesis agent
4. orchestrator_commit - persists memory and finalizes

Public API
----------
* build_triadic_graph - Construct and compile the state graph.
* run_triadic_prompt - Invoke the compiled graph with a user message.
* resume_triadic_interrupt - Resume graph execution after a C2 operator resolves an interrupt.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from singularity.core.agent_base import (
    AgentResponse,
    PromptPayload,
    RiskLevel,
)
from singularity.core.agent_registry import get_agent
from singularity.orchestration.state import TriadicState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Well-known agent IDs used by the graph
# ---------------------------------------------------------------------------

_SAFEGUARD_AGENT_ID = "safeguard-001"
_ORCHESTRATOR_AGENT_ID = "orchestrator-001"
_SYNTHESIS_AGENT_ID = "synthesis-001"

_INTERRUPT_RISK_THRESHOLD: set[RiskLevel] = {RiskLevel.HIGH, RiskLevel.CRITICAL}


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------

async def safeguard_screen(state: dict[str, Any]) -> dict[str, Any]:
    """Scan inbound payload using the Safeguard agent.
    
    If threats are detected, interrupts the graph and sets verdict to THREAT.
    """
    logger.info("🛡️ Safeguard screen — scanning payload")

    try:
        agent = get_agent(_SAFEGUARD_AGENT_ID)
    except KeyError:
        logger.warning(
            "Safeguard agent %r not found — skipping safeguard screen",
            _SAFEGUARD_AGENT_ID,
        )
        return {"security_verdict": "CLEAR"}

    payload = PromptPayload(
        source_agent_id="ground_control",
        target_agent_id=_SAFEGUARD_AGENT_ID,
        content=state.get("current_payload", ""),
    )

    response: AgentResponse = await agent.receive_prompt(payload)
    
    verdict = "CLEAR"
    interrupt_payload = {}
    is_interrupted = False
    
    for action in response.proposed_actions:
        if action.risk_level in _INTERRUPT_RISK_THRESHOLD:
            logger.warning(
                "⚠️ HIGH-RISK action proposed by %r: %s (risk=%s)",
                _SAFEGUARD_AGENT_ID,
                action.description,
                action.risk_level.value,
            )
            verdict = "THREAT"
            interrupt_payload = {
                "action_id": action.action_id,
                "agent_id": _SAFEGUARD_AGENT_ID,
                "action_type": action.action_type,
                "description": action.description,
                "risk_level": action.risk_level.value,
                "parameters": action.parameters,
            }
            is_interrupted = True
            
            # Fire an interrupt
            interrupt(interrupt_payload)
            break

    return {
        "messages": [AIMessage(content=response.content, name=_SAFEGUARD_AGENT_ID)],
        "security_verdict": verdict,
        "proposed_actions": response.proposed_actions,
        "interrupt_payload": interrupt_payload,
        "is_interrupted": is_interrupted,
    }


async def orchestrator_route(state: dict[str, Any]) -> dict[str, Any]:
    """Route payload using Orchestrator agent."""
    logger.info("⚙️ Orchestrator route — determining next steps")

    try:
        agent = get_agent(_ORCHESTRATOR_AGENT_ID)
    except KeyError:
        logger.warning("Orchestrator agent %r not found", _ORCHESTRATOR_AGENT_ID)
        return {"route_decision": "self_handle"}

    payload = PromptPayload(
        source_agent_id=_SAFEGUARD_AGENT_ID,
        target_agent_id=_ORCHESTRATOR_AGENT_ID,
        content=state.get("current_payload", ""),
    )

    response: AgentResponse = await agent.receive_prompt(payload)
    route_decision = response.metadata.get("route_to", "self_handle")

    return {
        "messages": [AIMessage(content=response.content, name=_ORCHESTRATOR_AGENT_ID)],
        "route_decision": route_decision,
        "proposed_actions": response.proposed_actions,
    }


async def synthesis_execute(state: dict[str, Any]) -> dict[str, Any]:
    """Execute the Synthesis agent to generate a combined response."""
    logger.info("🧠 Synthesis execute — generating output")

    try:
        agent = get_agent(_SYNTHESIS_AGENT_ID)
    except KeyError:
        logger.warning("Synthesis agent %r not found", _SYNTHESIS_AGENT_ID)
        return {"synthesis_output": ""}

    payload = PromptPayload(
        source_agent_id=_ORCHESTRATOR_AGENT_ID,
        target_agent_id=_SYNTHESIS_AGENT_ID,
        content=state.get("current_payload", ""),
    )

    response: AgentResponse = await agent.receive_prompt(payload)

    return {
        "messages": [AIMessage(content=response.content, name=_SYNTHESIS_AGENT_ID)],
        "synthesis_output": response.content,
        "proposed_actions": response.proposed_actions,
    }


async def orchestrator_commit(state: dict[str, Any]) -> dict[str, Any]:
    """Commit memory using Orchestrator agent."""
    logger.info("💾 Orchestrator commit — persisting memory")

    try:
        agent = get_agent(_ORCHESTRATOR_AGENT_ID)
        # Call commit_memory if available on the agent
        if hasattr(agent, "commit_memory"):
            input_text = state.get("current_payload", "")
            output_text = state.get("synthesis_output", "")
            await agent.commit_memory(input_text, output_text)
    except KeyError:
        pass

    return {
        "heartbeat_sequence": state.get("heartbeat_sequence", 0) + 1,
    }


# ---------------------------------------------------------------------------
# Conditional routing helpers
# ---------------------------------------------------------------------------

def _route_after_safeguard(state: dict[str, Any]) -> str:
    """Decide whether to route to orchestrator or end (if threat detected)."""
    if state.get("security_verdict") == "CLEAR":
        return "orchestrator_route"
    return END


def _route_after_orchestrator(state: dict[str, Any]) -> str:
    """Decide next steps based on orchestrator routing."""
    if state.get("route_decision") == "synthesis":
        return "synthesis_execute"
    return "orchestrator_commit"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_triadic_graph(
    checkpoint_path: str | Path = "triadic_checkpoints.sqlite",
) -> tuple[Any, AsyncSqliteSaver]:
    """Build and compile the Triadic state graph."""
    graph = StateGraph(TriadicState)

    # Register nodes
    graph.add_node("safeguard_screen", safeguard_screen)
    graph.add_node("orchestrator_route", orchestrator_route)
    graph.add_node("synthesis_execute", synthesis_execute)
    graph.add_node("orchestrator_commit", orchestrator_commit)

    # Edges
    graph.add_edge(START, "safeguard_screen")

    graph.add_conditional_edges(
        "safeguard_screen",
        _route_after_safeguard,
        {
            "orchestrator_route": "orchestrator_route",
            END: END,
        },
    )

    graph.add_conditional_edges(
        "orchestrator_route",
        _route_after_orchestrator,
        {
            "synthesis_execute": "synthesis_execute",
            "orchestrator_commit": "orchestrator_commit",
        },
    )

    graph.add_edge("synthesis_execute", "orchestrator_commit")
    graph.add_edge("orchestrator_commit", END)

    from langgraph.checkpoint.memory import MemorySaver
    checkpointer = MemorySaver()

    compiled = graph.compile(checkpointer=checkpointer)

    logger.info("Triadic state graph compiled with MemorySaver checkpointer")

    return compiled, checkpointer


# ---------------------------------------------------------------------------
# High-level invocation helpers
# ---------------------------------------------------------------------------

async def run_triadic_prompt(
    compiled_graph: Any,
    user_message: str,
    *,
    thread_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Invoke the triadic graph with a user message."""
    if thread_id is None:
        thread_id = uuid.uuid4().hex[:16]

    initial_state: dict[str, Any] = {
        "messages": [HumanMessage(content=user_message)],
        "current_payload": user_message,
        "security_verdict": "",
        "route_decision": "",
        "synthesis_output": "",
        "proposed_actions": [],
        "interrupt_payload": {},
        "memory_summary": "",
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

    logger.info("Invoking triadic graph — thread=%s", thread_id)

    result = await compiled_graph.ainvoke(initial_state, config=config)

    logger.info("Triadic graph execution complete — thread=%s", thread_id)

    return result


async def resume_triadic_interrupt(
    compiled_graph: Any,
    thread_id: str,
    resolution: dict[str, Any],
) -> dict[str, Any]:
    """Resume execution after an interrupt is resolved."""
    config: dict[str, Any] = {
        "configurable": {
            "thread_id": thread_id,
        },
    }

    logger.info("Resuming triadic graph — thread=%s", thread_id)

    result = await compiled_graph.ainvoke(
        Command(resume=resolution),
        config=config,
    )

    logger.info("Triadic graph resumed and completed — thread=%s", thread_id)

    return result
