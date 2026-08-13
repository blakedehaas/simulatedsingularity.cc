"""Heartbeat scheduler for the Simulated Singularity constellation.

Uses APScheduler's ``AsyncScheduler`` to broadcast periodic heartbeat
events every 60 seconds.  The scheduler interfaces with the persistence
layer's :class:`TaskRepository` for scheduled-task management and relies
on the agent registry to dispatch heartbeats to all active orbital nodes.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from singularity.neural_core.node_base import (
    NodeStatus,
    SystemPulse,
    DiagnosticFrame,
)
from singularity.neural_core.node_registry import get_agent, get_all_agents
from singularity.memory_vault.repository import TaskRepository

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


class HeartbeatScheduler:
    """APScheduler-backed heartbeat broadcaster for the constellation.

    Maintains a monotonically increasing sequence counter and dispatches
    :class:`SystemPulse` objects to every active agent on a fixed
    60-second interval.  Also exposes helpers for one-shot and recurring
    task scheduling via the persistence layer.

    Attributes:
        interval_seconds: Time between heartbeat broadcasts (default 60).
        is_running: Whether the scheduler loop is currently active.
    """

    def __init__(self, interval_seconds: int = 60) -> None:
        self.interval_seconds: int = interval_seconds
        self.is_running: bool = False
        self._sequence: int = 0
        self._scheduler: AsyncScheduler | None = None
        self._heartbeat_job_id: str = "heartbeat-broadcast"
        self._managed_job_ids: dict[str, str] = {}  # task_id -> apscheduler job_id

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the heartbeat scheduler."""
        if self.is_running:
            raise RuntimeError("HeartbeatScheduler is already running.")

        self._scheduler = AsyncIOScheduler()
        self._scheduler.start()

        self._scheduler.add_job(
            self.broadcast_heartbeat,
            trigger=IntervalTrigger(seconds=self.interval_seconds),
            id=self._heartbeat_job_id,
        )
        
        self._scheduler.add_job(
            self.execute_nightly_merge,
            trigger=CronTrigger(hour=2, minute=0),
            id="nightly-merge-job",
        )

        self.is_running = True
        logger.info(
            "HeartbeatScheduler started — broadcasting every %ds",
            self.interval_seconds,
        )

    async def stop(self) -> None:
        """Stop the heartbeat scheduler and clean up resources."""
        if not self.is_running:
            raise RuntimeError("HeartbeatScheduler is not running.")

        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None

        self.is_running = False
        self._managed_job_ids.clear()
        logger.info("HeartbeatScheduler stopped")

    async def start_triadic(self) -> None:
        """Start the heartbeat scheduler using triadic broadcast."""
        if self.is_running:
            raise RuntimeError("HeartbeatScheduler is already running.")

        self._scheduler = AsyncIOScheduler()
        self._scheduler.start()

        self._scheduler.add_job(
            self.broadcast_triadic_heartbeat,
            trigger=IntervalTrigger(seconds=self.interval_seconds),
            id=self._heartbeat_job_id,
        )

        self.is_running = True
        logger.info(
            "HeartbeatScheduler started (Triadic) — broadcasting every %ds",
            self.interval_seconds,
        )

    async def execute_nightly_merge(self) -> None:
        """Merge dev into main nightly and push."""
        logger.info("Executing nightly merge of dev into main...")
        try:
            from singularity.neural_core.github_tools import execute_git_command
            import asyncio
            
            await asyncio.to_thread(execute_git_command, "checkout main")
            await asyncio.to_thread(execute_git_command, "merge dev")
            await asyncio.to_thread(execute_git_command, "push origin main")
            logger.info("Nightly merge successful.")
        except Exception as e:
            logger.error(f"Nightly merge failed: {e}")

    # ------------------------------------------------------------------
    # Heartbeat broadcast
    # ------------------------------------------------------------------

    async def broadcast_heartbeat(self) -> list[DiagnosticFrame]:
        """Send a heartbeat event to every active agent in the constellation.

        Builds a :class:`SystemPulse` containing the current sequence
        number and a summary of every agent's status, then dispatches it
        to each agent's :meth:`process_heartbeat` method.

        Returns:
            A list of :class:`DiagnosticFrame` responses collected from
            agents that successfully processed the heartbeat.
        """
        self._sequence += 1

        agents = get_all_agents()
        constellation_summary: dict[str, NodeStatus] = {
            agent.node_id: agent.status for agent in agents
        }

        heartbeat = SystemPulse(
            sequence_number=self._sequence,
            constellation_summary=constellation_summary,
        )

        logger.info(
            "Broadcasting heartbeat #%d to %d agents",
            self._sequence,
            len(agents),
        )

        frames: list[DiagnosticFrame] = []
        for agent in agents:
            try:
                frame = await agent.process_heartbeat(heartbeat)
                frames.append(frame)
            except Exception:
                logger.exception(
                    "Agent %s failed to process heartbeat #%d",
                    agent.node_id,
                    self._sequence,
                )

        logger.info(
            "Heartbeat #%d complete — %d/%d agents responded",
            self._sequence,
            len(frames),
            len(agents),
        )
        return frames

    async def broadcast_triadic_heartbeat(self) -> list[DiagnosticFrame]:
        """Send a heartbeat event only to the triadic agents.
        
        Targets: orchestrator-001, safeguard-001, synthesis-001.

        Returns:
            A list of :class:`DiagnosticFrame` responses collected from
            agents that successfully processed the heartbeat.
        """
        self._sequence += 1

        all_agents = get_all_agents()
        triadic_ids = {"orchestrator-001", "safeguard-001", "synthesis-001"}
        agents = [a for a in all_agents if a.node_id in triadic_ids]

        constellation_summary: dict[str, NodeStatus] = {
            agent.node_id: agent.status for agent in agents
        }

        heartbeat = SystemPulse(
            sequence_number=self._sequence,
            constellation_summary=constellation_summary,
        )

        logger.info(
            "Broadcasting triadic heartbeat #%d to %d agents",
            self._sequence,
            len(agents),
        )

        frames: list[DiagnosticFrame] = []
        for agent in agents:
            try:
                frame = await agent.process_heartbeat(heartbeat)
                frames.append(frame)
            except Exception:
                logger.exception(
                    "Agent %s failed to process heartbeat #%d",
                    agent.node_id,
                    self._sequence,
                )

        logger.info(
            "Triadic heartbeat #%d complete — %d/%d agents responded",
            self._sequence,
            len(frames),
            len(agents),
        )
        return frames

    # ------------------------------------------------------------------

    # Scheduled task management
    # ------------------------------------------------------------------

    async def schedule_task(
        self,
        target_agent: str,
        prompt_text: str,
        delay_seconds: int = 0,
        interval_seconds: int = 0,
    ) -> str:
        """Schedule a prompt delivery task via the persistence layer.

        Creates a :class:`ScheduledTaskRecord` in the database and, if
        APScheduler is running, registers a corresponding job.

        Args:
            target_agent: ID of the target agent (or ``"all"`` for broadcast).
            prompt_text: The prompt text to deliver.
            delay_seconds: Seconds from now until first execution.
            interval_seconds: Recurrence interval (``0`` for one-shot).

        Returns:
            The ``task_id`` of the newly created scheduled task.
        """
        execute_at = _utc_now() + timedelta(seconds=delay_seconds)

        record = await TaskRepository.create_task(
            target_agent=target_agent,
            prompt_text=prompt_text,
            execute_at=execute_at,
            interval_seconds=interval_seconds,
        )
        task_id: str = record.task_id

        logger.info(
            "Scheduled task %s for agent %s at %s (interval=%ds)",
            task_id,
            target_agent,
            execute_at.isoformat(),
            interval_seconds,
        )
        return task_id

    async def cancel_task(self, task_id: str) -> None:
        """Cancel a previously scheduled task.

        Removes the task from the persistence layer and, if a
        corresponding APScheduler job exists, removes that too.

        Args:
            task_id: The unique identifier of the task to cancel.

        Raises:
            KeyError: If no task with the given ID exists.
        """
        record = await TaskRepository.get_task(task_id)
        if record is None:
            raise KeyError(f"No scheduled task with ID {task_id!r}")

        await TaskRepository.update_task_status(task_id, status="cancelled")

        if task_id in self._managed_job_ids and self._scheduler is not None:
            try:
                self._scheduler.remove_job(
                    self._managed_job_ids[task_id]
                )
            except Exception:
                logger.warning(
                    "APScheduler job for task %s could not be removed", task_id
                )
            del self._managed_job_ids[task_id]

        logger.info("Cancelled scheduled task %s", task_id)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def sequence_number(self) -> int:
        """Return the current heartbeat sequence number."""
        return self._sequence

    def __repr__(self) -> str:
        return (
            f"<HeartbeatScheduler "
            f"interval={self.interval_seconds}s "
            f"seq={self._sequence} "
            f"running={self.is_running}>"
        )
