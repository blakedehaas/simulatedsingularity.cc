"""Ground Control — Chainlit C2 dashboard application entry point.

Defines the Chainlit lifecycle hooks (``on_chat_start``, ``on_message``,
``on_stop``) and action callbacks that wire the human-in-the-loop dashboard
to the underlying constellation of agents, telemetry event bus, and
persistence layer.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import chainlit as cl
from chainlit import Action, Message

from singularity.core.agent_base import (
    AgentStatus,
    HeartbeatEvent,
    PromptPayload,
    TelemetryFrame,
)
from singularity.core.agent_registry import (
    get_agent,
    get_all_agents,
    initialize_constellation,
)
import singularity.agents  # Trigger @register_agent decorators
from dotenv import load_dotenv

load_dotenv()  # Load .env variables (e.g. GOOGLE_API_KEY)
from singularity.ground_control.components import (
    build_constellation_overview,
    build_heartbeat_indicator,
    build_sync_prompt_card,
    build_welcome_message,
)
from singularity.ground_control.handlers import (
    format_agent_response,
    format_telemetry,
    handle_heartbeat_trigger,
    handle_sync_prompt_response,
    handle_user_prompt,
)
from singularity.persistence.database import close_database, init_database
from singularity.telemetry.collector import TelemetryCollector
from singularity.telemetry.events import (
    TelemetryEvent,
    TelemetryEventBus,
    TelemetryEventType,
    get_event_bus,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers — session-scoped state management
# ---------------------------------------------------------------------------

def _store_session(key: str, value: Any) -> None:
    """Store a value in the current Chainlit user session.

    Args:
        key: Session storage key.
        value: The object to store.
    """
    cl.user_session.set(key, value)


def _get_session(key: str, default: Any = None) -> Any:
    """Retrieve a value from the current Chainlit user session.

    Args:
        key: Session storage key.
        default: Fallback value if the key is absent.

    Returns:
        The stored value, or *default*.
    """
    return cl.user_session.get(key, default)


# ---------------------------------------------------------------------------
# Telemetry event bridge → Chainlit messages
# ---------------------------------------------------------------------------

async def _on_telemetry_event(event: TelemetryEvent) -> None:
    """Bridge telemetry events into Chainlit as streamed messages.

    Called by the event bus whenever an interesting telemetry event occurs.
    Formats the event and sends it as a Chainlit message to the active
    session so the operator sees real-time updates.

    Args:
        event: The telemetry event to display.
    """
    emoji_map: dict[TelemetryEventType, str] = {
        TelemetryEventType.HEARTBEAT: "💓",
        TelemetryEventType.AGENT_RESPONSE: "📡",
        TelemetryEventType.INTERRUPT_RAISED: "🚨",
        TelemetryEventType.INTERRUPT_RESOLVED: "✅",
        TelemetryEventType.TASK_SCHEDULED: "📋",
        TelemetryEventType.TASK_COMPLETED: "🏁",
        TelemetryEventType.ERROR: "❌",
    }

    emoji = emoji_map.get(event.event_type, "📊")
    content = (
        f"{emoji} **{event.event_type.value.upper()}** — "
        f"`{event.source_agent_id}` at "
        f"`{event.timestamp.strftime('%H:%M:%S UTC')}`"
    )

    # Add data summary if present
    if event.data:
        summary_parts: list[str] = []
        for key, val in list(event.data.items())[:5]:
            summary_parts.append(f"  • **{key}**: {val}")
        if summary_parts:
            content += "\n" + "\n".join(summary_parts)

    try:
        await Message(content=content, author="Telemetry").send()
    except Exception:
        logger.exception("Failed to send telemetry event to Chainlit")


# ---------------------------------------------------------------------------
# Chainlit lifecycle hooks
# ---------------------------------------------------------------------------

@cl.on_chat_start
async def on_chat_start() -> None:
    """Initialize the constellation when a new Chainlit session begins.

    Performs the following startup sequence:
    1. Initialize the SQLite persistence layer.
    2. Instantiate all registered agents via the registry.
    3. Create and start the telemetry collector.
    4. Subscribe to telemetry events for real-time UI updates.
    5. Display the welcome message with constellation overview.
    """
    logger.info("Ground Control session starting")

    # Silence annoying Windows asyncio proactor connection lost errors
    import sys
    if sys.platform == 'win32':
        loop = asyncio.get_event_loop()
        def ignore_win_errors(loop, context):
            if isinstance(context.get('exception'), ConnectionResetError):
                return
            loop.default_exception_handler(context)
        loop.set_exception_handler(ignore_win_errors)

    # 1. Database
    try:
        await init_database()
        logger.info("Database initialized")
    except Exception:
        logger.exception("Database initialization failed")
        await Message(
            content="❌ **Database initialization failed.** Check logs for details.",
            author="Ground Control",
        ).send()
        return

    # 2. Constellation
    try:
        agents = initialize_constellation()
        _store_session("agents_initialized", True)
        logger.info("Constellation initialized with %d agents", len(agents))
    except Exception:
        logger.exception("Constellation initialization failed")
        await Message(
            content="❌ **Constellation initialization failed.** No agents registered.",
            author="Ground Control",
        ).send()
        agents = []

    # 3. Telemetry collector
    bus = get_event_bus()
    collector = TelemetryCollector(bus=bus)
    collector.start()
    _store_session("telemetry_collector", collector)
    _store_session("event_bus", bus)

    # 4. Subscribe UI bridge for non-heartbeat events (heartbeats are frequent)
    bus.subscribe(TelemetryEventType.INTERRUPT_RAISED, _on_telemetry_event)
    bus.subscribe(TelemetryEventType.INTERRUPT_RESOLVED, _on_telemetry_event)
    bus.subscribe(TelemetryEventType.ERROR, _on_telemetry_event)

    # 5. Welcome message
    welcome = build_welcome_message()
    await Message(content=welcome, author="Ground Control").send()

    if agents:
        overview = build_constellation_overview(agents)
        await Message(content=overview, author="Ground Control").send()

    # Add manual control actions
    actions = [
        Action(
            name="trigger_heartbeat",
            label="🫀 Manual Heartbeat",
            description="Trigger a manual heartbeat across all agents",
            payload={"action": "trigger_heartbeat"},
        ),
        Action(
            name="shutdown_system",
            label="🛑 Exit System",
            description="Gracefully shut down the C2 environment",
            payload={"action": "shutdown_system"},
        ),
    ]
    await Message(
        content="Use the actions below for manual constellation control:",
        author="Ground Control",
        actions=actions,
    ).send()

    logger.info("Ground Control session ready")


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Route an operator message through the orchestration pipeline.

    Wraps the operator's input as a :class:`PromptPayload`, invokes
    :func:`handle_user_prompt`, and displays the formatted response.

    Args:
        message: The Chainlit message from the operator.
    """
    content = message.content.strip()
    if not content:
        return

    logger.info("Operator message received: %s", content[:80])

    # Show a thinking indicator
    thinking_msg = Message(
        content="⏳ Processing through constellation...",
        author="Ground Control",
    )
    await thinking_msg.send()

    try:
        response, display_text = await handle_user_prompt(content)

        # Update the thinking message with the actual response
        await thinking_msg.remove()
        await Message(content=display_text, author="Ground Control").send()

        # If there are proposed actions requiring approval, show sync prompts
        if response and response.proposed_actions:
            for action in response.proposed_actions:
                from singularity.core.agent_base import InterruptRequest

                interrupt = InterruptRequest(proposed_action=action)
                card = build_sync_prompt_card(interrupt)
                await card.send()

    except Exception:
        logger.exception("Error processing operator message")
        await thinking_msg.remove()
        await Message(
            content="❌ **Error processing message.** Check Ground Control logs.",
            author="Ground Control",
        ).send()


@cl.on_stop
async def on_stop() -> None:
    """Gracefully shut down all constellation subsystems.

    Stops the telemetry collector, shuts down the event bus, and closes
    the database connection pool.
    """
    logger.info("Ground Control session stopping")

    # Stop telemetry collector
    collector: TelemetryCollector | None = _get_session("telemetry_collector")
    if collector is not None:
        collector.stop()

    # Shut down event bus
    bus: TelemetryEventBus | None = _get_session("event_bus")
    if bus is not None:
        await bus.shutdown()

    # Close database
    try:
        await close_database()
    except Exception:
        logger.exception("Error closing database")
        
    await asyncio.sleep(0.1) # allow proactor to finish transport closing

    logger.info("Ground Control session stopped")


# ---------------------------------------------------------------------------
# Action callbacks
# ---------------------------------------------------------------------------

@cl.action_callback("approve_action")
async def on_approve_action(action: Action) -> None:
    """Handle operator approval of a proposed action.

    Resolves the sync prompt as ``approved`` and publishes an
    INTERRUPT_RESOLVED event to the telemetry bus.

    Args:
        action: The Chainlit action containing the interrupt metadata.
    """
    action_id = action.value if hasattr(action, "value") and action.value else action.payload.get("value")
    logger.info("Operator APPROVED action %s", action_id)

    try:
        await handle_sync_prompt_response(
            action_id=action_id,
            resolution="approved",
            operator_id="ground_control_operator",
        )
        await Message(
            content=f"✅ **Action `{action_id}` APPROVED** — resuming execution.",
            author="Ground Control",
        ).send()

        # Publish resolution event
        bus: TelemetryEventBus | None = _get_session("event_bus")
        if bus is not None:
            await bus.publish(TelemetryEvent(
                event_type=TelemetryEventType.INTERRUPT_RESOLVED,
                source_agent_id="ground_control",
                data={"action_id": action_id, "resolution": "approved"},
            ))
    except Exception:
        logger.exception("Failed to process approval for %s", action_id)
        await Message(
            content=f"❌ Error processing approval for `{action_id}`.",
            author="Ground Control",
        ).send()

    await action.remove()


@cl.action_callback("deny_action")
async def on_deny_action(action: Action) -> None:
    """Handle operator denial of a proposed action.

    Resolves the sync prompt as ``denied`` and publishes an
    INTERRUPT_RESOLVED event to the telemetry bus.

    Args:
        action: The Chainlit action containing the interrupt metadata.
    """
    action_id = action.value if hasattr(action, "value") and action.value else action.payload.get("value")
    logger.info("Operator DENIED action %s", action_id)

    try:
        await handle_sync_prompt_response(
            action_id=action_id,
            resolution="denied",
            operator_id="ground_control_operator",
        )
        await Message(
            content=f"🚫 **Action `{action_id}` DENIED** — execution halted.",
            author="Ground Control",
        ).send()

        # Publish resolution event
        bus: TelemetryEventBus | None = _get_session("event_bus")
        if bus is not None:
            await bus.publish(TelemetryEvent(
                event_type=TelemetryEventType.INTERRUPT_RESOLVED,
                source_agent_id="ground_control",
                data={"action_id": action_id, "resolution": "denied"},
            ))
    except Exception:
        logger.exception("Failed to process denial for %s", action_id)
        await Message(
            content=f"❌ Error processing denial for `{action_id}`.",
            author="Ground Control",
        ).send()

    await action.remove()


@cl.action_callback("trigger_heartbeat")
async def on_trigger_heartbeat(action: Action) -> None:
    """Handle a manual heartbeat trigger from the operator.

    Dispatches a heartbeat to all agents and publishes the resulting
    telemetry frames to the event bus.

    Args:
        action: The Chainlit action that triggered this callback.
    """
    logger.info("Manual heartbeat triggered by operator")

    try:
        heartbeat_result = await handle_heartbeat_trigger()
        frames_summary = heartbeat_result.get("frames_collected", 0)

        await Message(
            content=(
                f"💓 **Manual heartbeat dispatched** — "
                f"{frames_summary} agent frames collected."
            ),
            author="Ground Control",
        ).send()

        # Publish heartbeat event
        bus: TelemetryEventBus | None = _get_session("event_bus")
        if bus is not None:
            await bus.publish(TelemetryEvent(
                event_type=TelemetryEventType.HEARTBEAT,
                source_agent_id="ground_control",
                data=heartbeat_result,
            ))
    except Exception:
        logger.exception("Manual heartbeat failed")
        await Message(
            content="❌ **Manual heartbeat failed.** Check logs.",
            author="Ground Control",
        ).send()


@cl.action_callback("shutdown_system")
async def on_shutdown_system(action: Action) -> None:
    """Handle manual system shutdown from the UI."""
    logger.info("Manual shutdown triggered from UI")
    await Message(
        content="🛑 **System Shutting Down**... You may now close this window.",
        author="Ground Control"
    ).send()
    
    # Trigger stop hooks cleanly
    await on_stop()
    
    import sys
    import os
    import signal
    
    # Attempt graceful shutdown
    if sys.platform == 'win32':
        os.kill(os.getpid(), signal.SIGTERM)
    else:
        sys.exit(0)
