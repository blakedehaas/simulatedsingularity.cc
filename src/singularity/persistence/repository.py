"""Data access layer for the flight data persistence store.

Provides repository classes that abstract all database operations behind
clean async interfaces, isolating the rest of the codebase from
SQLAlchemy query details.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from singularity.persistence.database import get_session
from singularity.persistence.models import (
    AgentMemoryRecord,
    AgentProfileRecord,
    CommunicationLogRecord,
    ExecutionStateRecord,
    ScheduledTaskRecord,
    SyncPromptRecord,
)

logger = logging.getLogger(__name__)


def _short_id() -> str:
    """Generate a short unique identifier."""
    return uuid.uuid4().hex[:12]


def _utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Agent Repository
# ---------------------------------------------------------------------------

class AgentRepository:
    """CRUD operations for agent profiles and interaction memories."""

    @staticmethod
    async def upsert_profile(
        agent_id: str,
        name: str,
        role: str,
        system_prompt: str = "",
        priority: int = 10,
    ) -> AgentProfileRecord:
        """Create or update an agent profile.

        Args:
            agent_id: Unique agent identifier.
            name: Human-readable display name.
            role: Agent's operational role description.
            system_prompt: The agent's system prompt text.
            priority: Routing priority.

        Returns:
            The created or updated ``AgentProfileRecord``.
        """
        async with get_session() as session:
            existing = await session.get(AgentProfileRecord, agent_id)
            if existing is not None:
                existing.name = name
                existing.role = role
                existing.system_prompt = system_prompt
                existing.priority = priority
                existing.updated_at = _utc_now()
                record = existing
            else:
                record = AgentProfileRecord(
                    agent_id=agent_id,
                    name=name,
                    role=role,
                    system_prompt=system_prompt,
                    priority=priority,
                )
                session.add(record)
            return record

    @staticmethod
    async def get_profile(agent_id: str) -> AgentProfileRecord | None:
        """Retrieve an agent profile by ID.

        Args:
            agent_id: The agent's unique identifier.

        Returns:
            The ``AgentProfileRecord`` if found, otherwise ``None``.
        """
        async with get_session() as session:
            return await session.get(AgentProfileRecord, agent_id)

    @staticmethod
    async def get_all_profiles() -> list[AgentProfileRecord]:
        """Retrieve all agent profiles ordered by priority.

        Returns:
            List of all ``AgentProfileRecord`` entries.
        """
        async with get_session() as session:
            result = await session.execute(
                select(AgentProfileRecord).order_by(AgentProfileRecord.priority)
            )
            return list(result.scalars().all())

    @staticmethod
    async def save_memory(
        agent_id: str,
        input_text: str,
        output_text: str,
    ) -> AgentMemoryRecord:
        """Record an agent interaction to memory.

        Args:
            agent_id: The agent that processed the interaction.
            input_text: The input prompt.
            output_text: The agent's response.

        Returns:
            The created ``AgentMemoryRecord``.
        """
        async with get_session() as session:
            record = AgentMemoryRecord(
                agent_id=agent_id,
                input_text=input_text,
                output_text=output_text,
            )
            session.add(record)
            return record

    @staticmethod
    async def get_memories(
        agent_id: str, limit: int = 50
    ) -> list[AgentMemoryRecord]:
        """Retrieve recent interaction memories for an agent.

        Args:
            agent_id: The agent's unique identifier.
            limit: Maximum number of records to return.

        Returns:
            List of ``AgentMemoryRecord`` entries, most recent first.
        """
        async with get_session() as session:
            result = await session.execute(
                select(AgentMemoryRecord)
                .where(AgentMemoryRecord.agent_id == agent_id)
                .order_by(AgentMemoryRecord.timestamp.desc())
                .limit(limit)
            )
            return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Task Repository
# ---------------------------------------------------------------------------

class TaskRepository:
    """CRUD operations for the scheduled task queue."""

    @staticmethod
    async def create_task(
        target_agent: str,
        prompt_text: str,
        execute_at: datetime,
        interval_seconds: int = 0,
    ) -> ScheduledTaskRecord:
        """Create a new scheduled task.

        Args:
            target_agent: ID of the target agent (or ``"all"``).
            prompt_text: The prompt to deliver.
            execute_at: When to execute.
            interval_seconds: Recurrence interval (``0`` for one-shot).

        Returns:
            The created ``ScheduledTaskRecord``.
        """
        async with get_session() as session:
            record = ScheduledTaskRecord(
                task_id=_short_id(),
                target_agent=target_agent,
                prompt_text=prompt_text,
                execute_at=execute_at,
                interval_seconds=interval_seconds,
            )
            session.add(record)
            return record

    @staticmethod
    async def get_task(task_id: str) -> ScheduledTaskRecord | None:
        """Retrieve a task by ID.

        Args:
            task_id: The task's unique identifier.

        Returns:
            The ``ScheduledTaskRecord`` if found, otherwise ``None``.
        """
        async with get_session() as session:
            return await session.get(ScheduledTaskRecord, task_id)

    @staticmethod
    async def get_pending_tasks() -> list[ScheduledTaskRecord]:
        """Retrieve all tasks with ``pending`` status.

        Returns:
            List of pending ``ScheduledTaskRecord`` entries.
        """
        async with get_session() as session:
            result = await session.execute(
                select(ScheduledTaskRecord)
                .where(ScheduledTaskRecord.status == "pending")
                .order_by(ScheduledTaskRecord.execute_at)
            )
            return list(result.scalars().all())

    @staticmethod
    async def update_task_status(
        task_id: str, status: str, result: str | None = None
    ) -> None:
        """Update a task's status and optional result.

        Args:
            task_id: The task's unique identifier.
            status: New status value.
            result: Optional result text.
        """
        async with get_session() as session:
            await session.execute(
                update(ScheduledTaskRecord)
                .where(ScheduledTaskRecord.task_id == task_id)
                .values(status=status, result=result)
            )

    @staticmethod
    async def delete_task(task_id: str) -> None:
        """Delete a task by ID.

        Args:
            task_id: The task's unique identifier.
        """
        async with get_session() as session:
            await session.execute(
                delete(ScheduledTaskRecord)
                .where(ScheduledTaskRecord.task_id == task_id)
            )


# ---------------------------------------------------------------------------
# Log Repository
# ---------------------------------------------------------------------------

class LogRepository:
    """Operations for the communication audit log."""

    @staticmethod
    async def log_communication(
        sender: str,
        recipient: str,
        message: str,
        log_level: str = "info",
    ) -> CommunicationLogRecord:
        """Record a communication event.

        Args:
            sender: Identifier of the sender.
            recipient: Identifier of the recipient.
            message: The message content.
            log_level: Severity level.

        Returns:
            The created ``CommunicationLogRecord``.
        """
        async with get_session() as session:
            record = CommunicationLogRecord(
                sender=sender,
                recipient=recipient,
                message=message,
                log_level=log_level,
            )
            session.add(record)
            return record

    @staticmethod
    async def get_recent_logs(limit: int = 100) -> list[CommunicationLogRecord]:
        """Retrieve recent communication logs.

        Args:
            limit: Maximum number of records.

        Returns:
            List of ``CommunicationLogRecord`` entries, most recent first.
        """
        async with get_session() as session:
            result = await session.execute(
                select(CommunicationLogRecord)
                .order_by(CommunicationLogRecord.timestamp.desc())
                .limit(limit)
            )
            return list(result.scalars().all())

    @staticmethod
    async def clear_logs() -> int:
        """Delete all communication logs.

        Returns:
            Number of records deleted.
        """
        async with get_session() as session:
            result = await session.execute(delete(CommunicationLogRecord))
            return result.rowcount  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# State Repository
# ---------------------------------------------------------------------------

class StateRepository:
    """Operations for execution state serialization and sync prompts."""

    @staticmethod
    async def save_state(
        graph_run_id: str,
        state_json: dict[str, Any],
    ) -> ExecutionStateRecord:
        """Serialize an execution state for interrupt/resume.

        Args:
            graph_run_id: The LangGraph run ID.
            state_json: JSON-serializable state snapshot.

        Returns:
            The created ``ExecutionStateRecord``.
        """
        async with get_session() as session:
            record = ExecutionStateRecord(
                state_id=_short_id(),
                graph_run_id=graph_run_id,
                state_json=state_json,
            )
            session.add(record)
            return record

    @staticmethod
    async def get_state(state_id: str) -> ExecutionStateRecord | None:
        """Retrieve an execution state by ID.

        Args:
            state_id: The state snapshot's unique identifier.

        Returns:
            The ``ExecutionStateRecord`` if found, otherwise ``None``.
        """
        async with get_session() as session:
            return await session.get(ExecutionStateRecord, state_id)

    @staticmethod
    async def resolve_state(
        state_id: str, status: str = "resumed"
    ) -> None:
        """Mark an execution state as resolved.

        Args:
            state_id: The state snapshot's unique identifier.
            status: Resolution status (``resumed`` or ``abandoned``).
        """
        async with get_session() as session:
            await session.execute(
                update(ExecutionStateRecord)
                .where(ExecutionStateRecord.state_id == state_id)
                .values(status=status, resolved_at=_utc_now())
            )

    @staticmethod
    async def create_sync_prompt(
        state_id: str,
        action_type: str,
        description: str,
        parameters_json: dict[str, Any] | None = None,
        risk_level: str = "low",
    ) -> SyncPromptRecord:
        """Create a new sync prompt for C2 review.

        Args:
            state_id: Foreign key to the execution state.
            action_type: Category of the proposed action.
            description: Human-readable description.
            parameters_json: Action parameters.
            risk_level: Assessed risk level.

        Returns:
            The created ``SyncPromptRecord``.
        """
        async with get_session() as session:
            record = SyncPromptRecord(
                prompt_id=_short_id(),
                state_id=state_id,
                action_type=action_type,
                description=description,
                parameters_json=parameters_json or {},
                risk_level=risk_level,
            )
            session.add(record)
            return record

    @staticmethod
    async def get_pending_sync_prompts() -> list[SyncPromptRecord]:
        """Retrieve all unresolved sync prompts.

        Returns:
            List of pending ``SyncPromptRecord`` entries.
        """
        async with get_session() as session:
            result = await session.execute(
                select(SyncPromptRecord)
                .where(SyncPromptRecord.resolution == "pending")
                .order_by(SyncPromptRecord.created_at)
            )
            return list(result.scalars().all())

    @staticmethod
    async def resolve_sync_prompt(
        prompt_id: str,
        resolution: str,
        resolved_by: str,
        modification_note: str | None = None,
    ) -> None:
        """Resolve a sync prompt with a C2 operator's decision.

        Args:
            prompt_id: The sync prompt's unique identifier.
            resolution: Decision (``approved``, ``denied``, ``modified``).
            resolved_by: Identifier of the resolving operator.
            modification_note: Optional note if the action was modified.
        """
        async with get_session() as session:
            await session.execute(
                update(SyncPromptRecord)
                .where(SyncPromptRecord.prompt_id == prompt_id)
                .values(
                    resolution=resolution,
                    resolved_by=resolved_by,
                    modification_note=modification_note,
                    resolved_at=_utc_now(),
                )
            )
