"""Ground Control message and action handlers.

Contains the business logic invoked by the Chainlit action callbacks
and message hooks.  Keeps the ``app.py`` thin by isolating orchestration
calls, response formatting, and HITL sync-prompt processing here.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from singularity.neural_core.node_base import (
    CognitiveOutput,
    NodeStatus,
    SystemPulse,
    C2InterventionRequest,
    SynapticTransmission,
    DiagnosticFrame,
)
from singularity.neural_core.node_registry import get_node, get_all_nodes
from singularity.memory_vault.repository import (
    LogRepository,
    StateRepository,
)
from singularity.sensorium.events import (
    SensoriumEvent,
    SensoriumEventType,
    get_event_bus,
)

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# User prompt handling
# ---------------------------------------------------------------------------

async def handle_user_prompt(
    message_content: str,
    target_node_id: str | None = None,
) -> tuple[CognitiveOutput | None, str]:
    """Wrap operator input as a SynapticTransmission and route through agents.

    Sends the prompt to the requested target agent, or the first available
    agent (by priority order) if no target is specified.
    Logs the communication and publishes a telemetry event on success.

    Args:
        message_content: Raw text from the Ground Control operator.
        target_node_id: The ID of the agent to route to directly.

    Returns:
        A tuple of ``(CognitiveOutput, formatted_display_text)``.  If no
        agents are available, returns ``(None, error_message)``.
    """
    agents = get_all_nodes()
    if not agents:
        error_text = (
            "⚠️ **No agents available.** The constellation has not been "
            "initialized or all agents are offline."
        )
        return None, error_text

    # Route to the requested agent or fallback to the highest-priority agent
    target_node = agents[0]
    if target_node_id:
        try:
            target_node = get_node(target_node_id)
        except KeyError:
            logger.warning("Target agent %s not found, falling back to %s", target_node_id, target_node.node_id)

    payload = SynapticTransmission(
        source_node_id="ground_control",
        target_node_id=target_node.node_id,
        content=message_content,
    )

    logger.info(
        "Routing prompt to %s (%s)",
        target_node.node_name,
        target_node.node_id,
    )

    try:
        response = await target_node.receive_prompt(payload)

        # Log the communication
        await LogRepository.log_communication(
            sender="ground_control",
            recipient=target_node.node_id,
            message=message_content,
        )
        await LogRepository.log_communication(
            sender=target_node.node_id,
            recipient="ground_control",
            message=response.content,
        )

        # Publish agent response event
        bus = get_event_bus()
        await bus.publish(SensoriumEvent(
            event_type=SensoriumEventType.NODE_RESPONSE,
            source_node_id=target_node.node_id,
            data={
                "content": response.content,
                "telemetry": response.telemetry.model_dump(mode="json"),
                "proposed_actions_count": len(response.action_proposals),
            },
        ))

        display_text = format_node_response(response)
        return response, display_text

    except Exception:
        logger.exception(
            "Agent %s failed to process prompt",
            target_node.node_id,
        )

        # Publish error event
        bus = get_event_bus()
        await bus.publish(SensoriumEvent(
            event_type=SensoriumEventType.ERROR,
            source_node_id=target_node.node_id,
            data={"message": f"Failed to process prompt: {message_content[:100]}"},
        ))

        error_text = (
            f"❌ **Agent `{target_node.node_name}` failed to process "
            f"the prompt.** The error has been logged."
        )
        return None, error_text


# ---------------------------------------------------------------------------
# Triadic prompt handling
# ---------------------------------------------------------------------------

_triadic_graph: CompiledStateGraph | None = None

async def handle_triadic_prompt(
    message_content: str, thread_id: str | None = None
) -> tuple[Any | None, str]:
    """Handle a user prompt through the triadic orchestrator graph.
    
    Builds the graph if not cached, runs it, and formats the response.
    
    Args:
        message_content: Raw text from the Ground Control operator.
        thread_id: Thread ID for persistence state.
        
    Returns:
        A tuple of ``(state, formatted_display_text)``.
    """
    global _triadic_graph
    
    try:
        from singularity.swarm_orchestration.triadic_graph import (
            build_triadic_graph,
            run_triadic_prompt,
        )
    except ImportError:
        return None, "❌ Triadic graph module not available."
        
    from singularity.neural_core.node_registry import initialize_constellation, get_all_nodes
    from singularity.memory_vault.database import init_database
    import singularity.cognitive_nodes

    try:
        await init_database()
    except Exception:
        pass

    if not get_all_nodes():
        initialize_constellation()

    if _triadic_graph is None:
        _triadic_graph, _ = build_triadic_graph()

    try:
        final_state = await run_triadic_prompt(_triadic_graph, message_content, thread_id=thread_id)
        
        # Check if the state provides a direct agent response to format
        # If it doesn't, we fallback to a generic message format
        response = final_state.get("final_response") if isinstance(final_state, dict) else None
        
        if isinstance(response, CognitiveOutput):
            display_text = format_node_response(response)
        else:
            display_text = "### 📐 Triadic Architecture Update\nGraph execution completed successfully."
            
        return final_state, display_text

    except Exception:
        logger.exception("Failed to process triadic prompt")
        return None, "❌ **Triadic pipeline failed to process the prompt.** The error has been logged."

async def handle_triadic_interrupt_response(
    thread_id: str, resolution_payload: Any
) -> tuple[Any | None, str]:
    """Resume an interrupted triadic graph.
    
    Args:
        thread_id: Thread ID identifying the paused state.
        resolution_payload: The approval/denial payload.
        
    Returns:
        A tuple of ``(state, formatted_display_text)``.
    """
    global _triadic_graph
    
    try:
        from singularity.swarm_orchestration.triadic_graph import build_triadic_graph
    except ImportError:
        return None, "❌ Triadic graph module not available."
        
    if _triadic_graph is None:
        _triadic_graph, _ = build_triadic_graph()
        
    try:
        config = {"configurable": {"thread_id": thread_id}}
        final_state = await _triadic_graph.ainvoke(Command(resume=resolution_payload), config)
        
        response = final_state.get("final_response") if isinstance(final_state, dict) else None
        
        if isinstance(response, CognitiveOutput):
            display_text = format_node_response(response)
        else:
            display_text = "### 📐 Triadic Architecture Update\nGraph resumed and completed successfully."
            
        return final_state, display_text
        
    except Exception:
        logger.exception("Failed to resume triadic graph")
        return None, "❌ **Failed to resume triadic graph.** The error has been logged."

# ---------------------------------------------------------------------------

# Sync prompt (HITL) resolution
# ---------------------------------------------------------------------------

async def handle_sync_prompt_response(
    action_id: str,
    resolution: str,
    operator_id: str,
    modification_note: str | None = None,
) -> None:
    """Process an operator's decision on a sync prompt / interrupt.

    Persists the resolution to the database and logs the decision.

    Args:
        action_id: The unique ID of the action / sync prompt.
        resolution: The decision — ``approved``, ``denied``, or ``modified``.
        operator_id: Identifier of the operator who made the decision.
        modification_note: Optional note when the action is modified.
    """
    logger.info(
        "Sync prompt %s resolved as %s by %s",
        action_id,
        resolution,
        operator_id,
    )

    try:
        await StateRepository.resolve_sync_prompt(
            prompt_id=action_id,
            resolution=resolution,
            resolved_by=operator_id,
            modification_note=modification_note,
        )
    except Exception:
        logger.exception("Failed to persist sync prompt resolution for %s", action_id)
        raise

    # Audit log
    await LogRepository.log_communication(
        sender=operator_id,
        recipient="orchestration",
        message=f"Sync prompt {action_id} resolved: {resolution}",
        log_level="info",
    )


# ---------------------------------------------------------------------------
# Heartbeat trigger
# ---------------------------------------------------------------------------

async def handle_pulse_trigger() -> dict[str, Any]:
    """Dispatch a manual heartbeat to all agents in the constellation.

    Calls :meth:`process_heartbeat` on every registered agent, collects
    their telemetry frames, and returns summary statistics.

    Returns:
        A dictionary with heartbeat results including frame count and
        per-agent status summaries.
    """
    agents = get_all_nodes()
    if not agents:
        return {"frames_collected": 0, "agents": [], "error": "No agents available"}

    # Build constellation summary from current statuses
    constellation_summary: dict[str, NodeStatus] = {
        agent.node_id: agent.status for agent in agents
    }

    heartbeat = SystemPulse(
        sequence_number=0,  # Manual heartbeats use sequence 0
        constellation_summary=constellation_summary,
    )

    frames: list[dict[str, Any]] = []
    errors: list[str] = []

    for agent in agents:
        try:
            frame = await agent.process_heartbeat(heartbeat)
            frames.append({
                "node_id": frame.node_id,
                "status": frame.status.value,
                "metrics": frame.metrics,
                "message": frame.message,
            })
        except Exception:
            logger.exception(
                "Heartbeat failed for agent %s",
                agent.node_id,
            )
            errors.append(agent.node_id)

    result: dict[str, Any] = {
        "frames_collected": len(frames),
        "frames": frames,
        "errors": errors,
        "total_agents": len(agents),
    }

    logger.info(
        "Manual heartbeat complete: %d/%d frames collected",
        len(frames),
        len(agents),
    )

    return result


# ---------------------------------------------------------------------------
# Response formatting
# ---------------------------------------------------------------------------

def format_node_response(response: CognitiveOutput) -> str:
    """Format an CognitiveOutput for display in the Chainlit UI.

    Renders the response content, telemetry summary, and any proposed
    actions as a structured Markdown string.

    Args:
        response: The agent response to format.

    Returns:
        A Markdown-formatted string for display.
    """
    status_emoji: dict[NodeStatus, str] = {
        NodeStatus.INITIALIZING: "🔄",
        NodeStatus.NOMINAL: "🟢",
        NodeStatus.BUSY: "🟡",
        NodeStatus.INTERRUPTED: "🟠",
        NodeStatus.ERROR: "🔴",
        NodeStatus.OFFLINE: "⚫",
    }

    telemetry = response.telemetry
    emoji = status_emoji.get(telemetry.status, "⚪")

    lines: list[str] = [
        f"### 📡 Response from `{response.node_id}`",
        "",
        response.content,
        "",
        "---",
        f"**Telemetry** {emoji} `{telemetry.status.value.upper()}`",
    ]

    if telemetry.metrics:
        lines.append("")
        for key, value in telemetry.metrics.items():
            lines.append(f"  • **{key}**: `{value}`")

    if telemetry.message:
        lines.append(f"  • *{telemetry.message}*")

    if response.action_proposals:
        lines.append("")
        lines.append(
            f"⚠️ **{len(response.action_proposals)} proposed action(s)** "
            "require approval:"
        )
        for action in response.action_proposals:
            lines.append(
                f"  • `{action.action_type}` — {action.description} "
                f"(Risk: **{action.risk_level.value}**)"
            )

    return "\n".join(lines)


def format_diagnostics(frame: DiagnosticFrame) -> str:
    """Format a DiagnosticFrame as a compact status string.

    Intended for use as inline telemetry annotations in the Chainlit
    message stream.

    Args:
        frame: The telemetry frame to format.

    Returns:
        A single-line Markdown-formatted telemetry summary.
    """
    status_emoji: dict[NodeStatus, str] = {
        NodeStatus.INITIALIZING: "🔄",
        NodeStatus.NOMINAL: "🟢",
        NodeStatus.BUSY: "🟡",
        NodeStatus.INTERRUPTED: "🟠",
        NodeStatus.ERROR: "🔴",
        NodeStatus.OFFLINE: "⚫",
    }

    emoji = status_emoji.get(frame.status, "⚪")
    timestamp_str = frame.timestamp.strftime("%H:%M:%S")

    parts = [
        f"{emoji} `{frame.node_id}` — **{frame.status.value}** @ {timestamp_str}",
    ]

    if frame.metrics:
        metric_strs = [f"{k}={v}" for k, v in frame.metrics.items()]
        parts.append(f"  [{', '.join(metric_strs)}]")

    if frame.message:
        parts.append(f"  *{frame.message}*")

    return " ".join(parts)
