"""Telemetry event bus — async pub/sub for constellation-wide events.

Provides a decoupled publish/subscribe mechanism built on ``asyncio.Queue``
so that telemetry producers (agents, scheduler, orchestration) and consumers
(Ground Control UI, collectors, loggers) operate independently without
blocking each other.
"""

from __future__ import annotations

import asyncio
import enum
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Awaitable, Callable

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

class TelemetryEventType(str, enum.Enum):
    """Classification of telemetry events flowing through the event bus."""

    HEARTBEAT = "heartbeat"
    AGENT_RESPONSE = "agent_response"
    INTERRUPT_RAISED = "interrupt_raised"
    INTERRUPT_RESOLVED = "interrupt_resolved"
    TASK_SCHEDULED = "task_scheduled"
    TASK_COMPLETED = "task_completed"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Event model
# ---------------------------------------------------------------------------

def _utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


def _new_event_id() -> str:
    """Generate a unique event identifier."""
    return uuid.uuid4().hex[:16]


class TelemetryEvent(BaseModel):
    """A single telemetry event emitted by a constellation component.

    Attributes:
        event_id: Unique identifier for this event instance.
        event_type: Classification of the event (heartbeat, error, etc.).
        source_agent_id: ID of the agent or component that produced the event.
        data: Arbitrary payload data specific to the event type.
        timestamp: UTC timestamp when the event was created.
    """

    event_id: str = Field(default_factory=_new_event_id)
    event_type: TelemetryEventType
    source_agent_id: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utc_now)


# Type alias for subscriber callbacks
EventHandler = Callable[[TelemetryEvent], Awaitable[None]]


# ---------------------------------------------------------------------------
# Event bus singleton
# ---------------------------------------------------------------------------

class TelemetryEventBus:
    """Async publish/subscribe event bus for telemetry distribution.

    Uses per-subscriber ``asyncio.Queue`` instances so that slow consumers
    do not block fast publishers.  Handlers registered via :meth:`subscribe`
    are invoked concurrently when an event is published.  The :meth:`stream`
    async generator yields matching events for pull-based consumption.

    Attributes:
        _handlers: Mapping of event types to their registered async handlers.
        _queues: Active subscriber queues for the ``stream`` interface.
        _running: Whether the bus is accepting events.
    """

    def __init__(self, max_queue_size: int = 1024) -> None:
        self._handlers: dict[TelemetryEventType, list[EventHandler]] = defaultdict(list)
        self._queues: list[asyncio.Queue[TelemetryEvent | None]] = []
        self._max_queue_size = max_queue_size
        self._running: bool = True
        logger.info("TelemetryEventBus initialized (queue capacity=%d)", max_queue_size)

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def publish(self, event: TelemetryEvent) -> None:
        """Broadcast a telemetry event to all matching subscribers.

        Dispatches to both registered async handler callbacks and any
        active ``stream()`` queues.  Handler exceptions are logged but
        do not propagate, ensuring one misbehaving subscriber cannot
        crash the bus.

        Args:
            event: The telemetry event to broadcast.
        """
        if not self._running:
            logger.warning(
                "Event bus is shut down — dropping event %s from %s",
                event.event_id,
                event.source_agent_id,
            )
            return

        logger.debug(
            "Publishing %s event %s from %s",
            event.event_type.value,
            event.event_id,
            event.source_agent_id,
        )

        # Dispatch to registered handlers
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    "Handler %s failed for event %s",
                    handler.__qualname__,
                    event.event_id,
                )

        # Enqueue for stream consumers
        for queue in self._queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "Stream queue full — dropping event %s for a slow consumer",
                    event.event_id,
                )

    # ------------------------------------------------------------------
    # Subscription (callback-based)
    # ------------------------------------------------------------------

    def subscribe(
        self,
        event_type: TelemetryEventType,
        handler: EventHandler,
    ) -> None:
        """Register an async callback for a specific event type.

        The handler will be ``await``-ed every time an event of the
        given type is published.

        Args:
            event_type: The event type to listen for.
            handler: An async callable ``(TelemetryEvent) -> None``.
        """
        self._handlers[event_type].append(handler)
        logger.info(
            "Subscribed %s to %s events",
            handler.__qualname__,
            event_type.value,
        )

    def unsubscribe(
        self,
        event_type: TelemetryEventType,
        handler: EventHandler,
    ) -> None:
        """Remove a previously registered handler.

        Args:
            event_type: The event type the handler was registered for.
            handler: The handler to remove.

        Raises:
            ValueError: If the handler is not registered for the event type.
        """
        try:
            self._handlers[event_type].remove(handler)
            logger.info(
                "Unsubscribed %s from %s events",
                handler.__qualname__,
                event_type.value,
            )
        except ValueError:
            raise ValueError(
                f"Handler {handler.__qualname__} is not subscribed to "
                f"{event_type.value} events."
            )

    # ------------------------------------------------------------------
    # Subscription (pull-based async generator)
    # ------------------------------------------------------------------

    async def stream(
        self,
        event_types: list[TelemetryEventType] | None = None,
    ) -> AsyncIterator[TelemetryEvent]:
        """Async generator that yields matching telemetry events.

        Creates an internal queue and yields events as they arrive.
        If ``event_types`` is provided, only matching events are yielded;
        otherwise all events are forwarded.

        Args:
            event_types: Optional filter — only yield events whose type
                is in this list.  ``None`` means yield everything.

        Yields:
            Matching :class:`TelemetryEvent` instances.
        """
        queue: asyncio.Queue[TelemetryEvent | None] = asyncio.Queue(
            maxsize=self._max_queue_size,
        )
        self._queues.append(queue)
        type_set = set(event_types) if event_types else None

        try:
            while self._running:
                event = await queue.get()
                if event is None:
                    # Sentinel — bus is shutting down
                    break
                if type_set is None or event.event_type in type_set:
                    yield event
        finally:
            self._queues.remove(queue)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def shutdown(self) -> None:
        """Gracefully shut down the event bus.

        Sends a ``None`` sentinel to every active stream queue so that
        ``stream()`` generators exit cleanly, then clears all handlers.
        """
        logger.info("Shutting down TelemetryEventBus")
        self._running = False

        # Signal all stream consumers to exit
        for queue in self._queues:
            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                pass

        self._handlers.clear()
        logger.info("TelemetryEventBus shutdown complete")

    def reset(self) -> None:
        """Reset the bus to a clean state (primarily for testing).

        Clears all handlers and queues without sending sentinels.
        """
        self._handlers.clear()
        self._queues.clear()
        self._running = True
        logger.debug("TelemetryEventBus reset")


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_bus_instance: TelemetryEventBus | None = None


def get_event_bus() -> TelemetryEventBus:
    """Return the module-level event bus singleton, creating it on first call.

    Returns:
        The shared :class:`TelemetryEventBus` instance.
    """
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = TelemetryEventBus()
    return _bus_instance


def reset_event_bus() -> None:
    """Replace the singleton with a fresh instance (for testing)."""
    global _bus_instance
    if _bus_instance is not None:
        _bus_instance.reset()
    _bus_instance = TelemetryEventBus()
