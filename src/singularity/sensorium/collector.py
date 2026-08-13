"""Telemetry collector — aggregates agent metrics across the constellation.

Listens on the :class:`TelemetryEventBus` for heartbeat and agent-response
events, accumulates the latest :class:`DiagnosticFrame` per agent, and
exposes a single-call method to retrieve the full constellation status.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from singularity.neural_core.node_base import (
    NodeStatus,
    CognitiveNode,
    DiagnosticFrame,
)
from singularity.neural_core.node_registry import get_all_agents
from singularity.sensorium.events import (
    TelemetryEvent,
    TelemetryEventBus,
    TelemetryEventType,
    get_event_bus,
)

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


class TelemetryCollector:
    """Aggregates telemetry frames and heartbeat statistics.

    Subscribes to the :class:`TelemetryEventBus` to collect
    :class:`DiagnosticFrame` snapshots emitted by agents and the
    scheduler.  Maintains an in-memory cache of the latest frame
    per agent and a running heartbeat counter.

    Attributes:
        _latest_frames: Most recent telemetry frame per agent ID.
        _heartbeat_count: Total number of heartbeats received.
        _last_heartbeat_at: Timestamp of the most recent heartbeat.
        _bus: The event bus this collector is subscribed to.
    """

    def __init__(self, bus: TelemetryEventBus | None = None) -> None:
        self._bus: TelemetryEventBus = bus or get_event_bus()
        self._latest_frames: dict[str, DiagnosticFrame] = {}
        self._heartbeat_count: int = 0
        self._last_heartbeat_at: datetime | None = None
        self._started: bool = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Subscribe to the event bus for heartbeat and response events.

        Safe to call multiple times; subsequent calls are no-ops.
        """
        if self._started:
            logger.debug("TelemetryCollector already started — skipping")
            return

        self._bus.subscribe(TelemetryEventType.HEARTBEAT, self._on_heartbeat)
        self._bus.subscribe(TelemetryEventType.AGENT_RESPONSE, self._on_agent_response)
        self._bus.subscribe(TelemetryEventType.ERROR, self._on_error)
        self._started = True
        logger.info("TelemetryCollector started — listening for events")

    def stop(self) -> None:
        """Unsubscribe from the event bus.

        Safe to call even if :meth:`start` was never called.
        """
        if not self._started:
            return

        try:
            self._bus.unsubscribe(TelemetryEventType.HEARTBEAT, self._on_heartbeat)
            self._bus.unsubscribe(TelemetryEventType.AGENT_RESPONSE, self._on_agent_response)
            self._bus.unsubscribe(TelemetryEventType.ERROR, self._on_error)
        except ValueError:
            logger.debug("Handler already removed during unsubscribe")

        self._started = False
        logger.info("TelemetryCollector stopped")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def _on_heartbeat(self, event: TelemetryEvent) -> None:
        """Handle a heartbeat event from the scheduler.

        Updates heartbeat counter and extracts any embedded telemetry
        frames from the event data.

        Args:
            event: The heartbeat telemetry event.
        """
        self._heartbeat_count += 1
        self._last_heartbeat_at = event.timestamp
        logger.debug(
            "Heartbeat #%d received from %s",
            self._heartbeat_count,
            event.source_node_id,
        )

        # If the heartbeat includes per-agent frames, store them
        frames_data: list[dict[str, Any]] = event.data.get("frames", [])
        for frame_dict in frames_data:
            try:
                frame = DiagnosticFrame(**frame_dict)
                self._latest_frames[frame.node_id] = frame
            except Exception:
                logger.exception("Failed to parse telemetry frame from heartbeat data")

    async def _on_agent_response(self, event: TelemetryEvent) -> None:
        """Handle an agent response event carrying a telemetry frame.

        Args:
            event: The agent-response telemetry event.
        """
        frame_dict: dict[str, Any] | None = event.data.get("telemetry")
        if frame_dict is not None:
            try:
                frame = DiagnosticFrame(**frame_dict)
                self._latest_frames[frame.node_id] = frame
                logger.debug(
                    "Updated telemetry frame for agent %s (status=%s)",
                    frame.node_id,
                    frame.status.value,
                )
            except Exception:
                logger.exception(
                    "Failed to parse telemetry frame from agent response event %s",
                    event.event_id,
                )

    async def _on_error(self, event: TelemetryEvent) -> None:
        """Handle an error event and mark the agent's cached status.

        Args:
            event: The error telemetry event.
        """
        node_id = event.source_node_id
        error_msg = event.data.get("message", "Unknown error")
        logger.warning(
            "Error event from %s: %s",
            node_id,
            error_msg,
        )

        # Update or create a frame reflecting the error state
        self._latest_frames[node_id] = DiagnosticFrame(
            node_id=node_id,
            status=NodeStatus.ERROR,
            message=error_msg,
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_latest_frame(self, node_id: str) -> DiagnosticFrame | None:
        """Return the most recent telemetry frame for a specific agent.

        Args:
            node_id: The agent's unique identifier.

        Returns:
            The latest :class:`DiagnosticFrame`, or ``None`` if no frames
            have been received from this agent.
        """
        return self._latest_frames.get(node_id)

    async def collect_live_telemetry(self) -> list[DiagnosticFrame]:
        """Poll every registered agent for a fresh telemetry frame.

        Calls :meth:`CognitiveNode.emit_telemetry` on each agent from
        the registry and updates the internal cache.

        Returns:
            List of freshly collected :class:`DiagnosticFrame` instances.
        """
        frames: list[DiagnosticFrame] = []
        agents = get_all_agents()

        for agent in agents:
            try:
                frame = await agent.emit_telemetry()
                self._latest_frames[frame.node_id] = frame
                frames.append(frame)
            except Exception:
                logger.exception(
                    "Failed to collect telemetry from agent %s",
                    agent.node_id,
                )
                error_frame = DiagnosticFrame(
                    node_id=agent.node_id,
                    status=NodeStatus.ERROR,
                    message="Telemetry collection failed",
                )
                self._latest_frames[agent.node_id] = error_frame
                frames.append(error_frame)

        return frames

    def get_constellation_status(self) -> dict[str, Any]:
        """Return a comprehensive snapshot of the constellation's state.

        Aggregates cached telemetry frames, heartbeat statistics, and
        live agent information from the registry.

        Returns:
            A dictionary containing:
            - ``agents``: per-agent status dicts with name, role, status, metrics.
            - ``heartbeat_count``: total heartbeats received.
            - ``last_heartbeat_at``: ISO timestamp of last heartbeat.
            - ``total_agents``: count of registered agents.
            - ``agents_nominal``: count of agents in NOMINAL status.
            - ``agents_error``: count of agents in ERROR status.
            - ``collected_at``: ISO timestamp of this snapshot.
        """
        agents_info: list[dict[str, Any]] = []
        nominal_count = 0
        error_count = 0

        all_agents = get_all_agents()
        for agent in all_agents:
            cached_frame = self._latest_frames.get(agent.node_id)
            status = cached_frame.status if cached_frame else agent.status
            metrics = cached_frame.metrics if cached_frame else {}
            message = cached_frame.message if cached_frame else ""

            if status == NodeStatus.NOMINAL:
                nominal_count += 1
            elif status == NodeStatus.ERROR:
                error_count += 1

            agents_info.append({
                "node_id": agent.node_id,
                "node_name": agent.node_name,
                "node_role": agent.node_role,
                "status": status.value,
                "priority": agent.priority,
                "metrics": metrics,
                "message": message,
                "last_frame_at": (
                    cached_frame.timestamp.isoformat()
                    if cached_frame
                    else None
                ),
            })

        return {
            "agents": agents_info,
            "heartbeat_count": self._heartbeat_count,
            "last_heartbeat_at": (
                self._last_heartbeat_at.isoformat()
                if self._last_heartbeat_at
                else None
            ),
            "total_agents": len(all_agents),
            "agents_nominal": nominal_count,
            "agents_error": error_count,
            "collected_at": _utc_now().isoformat(),
        }

    @property
    def heartbeat_count(self) -> int:
        """Total number of heartbeats received since collector start."""
        return self._heartbeat_count

    @property
    def last_heartbeat_at(self) -> datetime | None:
        """Timestamp of the most recent heartbeat, or ``None``."""
        return self._last_heartbeat_at
