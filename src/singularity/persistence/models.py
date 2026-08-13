"""SQLAlchemy ORM models for the flight data persistence layer.

Defines the relational schema for agent profiles, interaction memory,
scheduled tasks, communication logs, execution states, and sync prompts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class AgentProfileRecord(Base):
    """Persistent configuration and system prompt for an agent.

    Attributes:
        agent_id: Primary key — unique agent identifier.
        name: Human-readable display name.
        role: Description of the agent's operational role.
        system_prompt: The agent's system prompt text.
        priority: Routing priority (lower = higher).
        is_active: Whether the agent is currently active.
        created_at: When the profile was first created.
        updated_at: When the profile was last modified.
    """

    __tablename__ = "agent_profiles"

    agent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(256), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[int] = mapped_column(Integer, default=10)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now
    )

    # Relationships
    memories: Mapped[list[AgentMemoryRecord]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )


class AgentMemoryRecord(Base):
    """An agent's input/output interaction log entry.

    Attributes:
        id: Auto-incrementing primary key.
        agent_id: Foreign key to the agent profile.
        input_text: The prompt text received by the agent.
        output_text: The response produced by the agent.
        timestamp: When the interaction occurred.
    """

    __tablename__ = "agent_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("agent_profiles.agent_id"), nullable=False
    )
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    output_text: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )

    # Relationships
    agent: Mapped[AgentProfileRecord] = relationship(back_populates="memories")


class ScheduledTaskRecord(Base):
    """A task queued for execution by the Mission Scheduler.

    Attributes:
        task_id: Primary key — short UUID.
        target_agent: ID of the agent (or ``"all"`` for broadcast).
        prompt_text: The prompt to deliver when the task fires.
        execute_at: Scheduled execution time.
        interval_seconds: Recurrence interval (``0`` for one-shot).
        status: Current task status (``pending``, ``running``, ``completed``, ``failed``).
        result: Output from execution (if completed).
        created_at: When the task was created.
    """

    __tablename__ = "scheduled_tasks"

    task_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    target_agent: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    execute_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    interval_seconds: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )


class CommunicationLogRecord(Base):
    """Audit log entry for inter-agent and Ground Control communications.

    Attributes:
        id: Auto-incrementing primary key.
        sender: Identifier of the message sender.
        recipient: Identifier of the message recipient.
        message: The message content.
        log_level: Log severity level (``info``, ``warning``, ``error``).
        timestamp: When the communication occurred.
    """

    __tablename__ = "communication_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender: Mapped[str] = mapped_column(String(128), nullable=False)
    recipient: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    log_level: Mapped[str] = mapped_column(String(32), default="info")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )


class ExecutionStateRecord(Base):
    """Serialized LangGraph execution state for interrupt/resume.

    When a graph execution is interrupted for C2 review, the full state
    is serialized here so it can be restored upon approval.

    Attributes:
        state_id: Primary key — unique state snapshot identifier.
        graph_run_id: The LangGraph run ID this state belongs to.
        state_json: JSON-serialized execution state.
        status: Current status (``paused``, ``resumed``, ``abandoned``).
        created_at: When the state was captured.
        resolved_at: When the state was resumed or abandoned.
    """

    __tablename__ = "execution_states"

    state_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    graph_run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    state_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="paused")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    sync_prompts: Mapped[list[SyncPromptRecord]] = relationship(
        back_populates="execution_state", cascade="all, delete-orphan"
    )


class SyncPromptRecord(Base):
    """A pending human-in-the-loop approval request.

    Created when a LangGraph interrupt is triggered. The C2 operator
    must approve, deny, or modify the proposed action before the graph
    can resume.

    Attributes:
        prompt_id: Primary key — unique sync prompt identifier.
        state_id: Foreign key to the execution state.
        action_type: Category of the proposed action.
        description: Human-readable description of the action.
        parameters_json: JSON-serialized action parameters.
        risk_level: Assessed risk level.
        resolution: Outcome (``pending``, ``approved``, ``denied``, ``modified``).
        resolved_by: Identifier of the operator who resolved.
        modification_note: Note attached if the action was modified.
        created_at: When the sync prompt was created.
        resolved_at: When the sync prompt was resolved.
    """

    __tablename__ = "sync_prompts"

    prompt_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    state_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("execution_states.state_id"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    parameters_json: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_level: Mapped[str] = mapped_column(String(32), default="low")
    resolution: Mapped[str] = mapped_column(String(32), default="pending")
    resolved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    modification_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    execution_state: Mapped[ExecutionStateRecord] = relationship(
        back_populates="sync_prompts"
    )

class AgentScratchpadLog(Base):
    """Raw uncompacted context entries for agent scratchpads.

    Attributes:
        id: Auto-incrementing primary key.
        agent_id: Foreign key to the agent profile.
        entry_text: The raw text added to the scratchpad.
        timestamp: When the entry was added.
    """

    __tablename__ = "agent_scratchpad_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_text: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )


class MemorySummaryRecord(Base):
    """Compacted interaction memory summary for an agent.

    Attributes:
        id: Auto-incrementing primary key.
        agent_id: Foreign key or identifier for the agent.
        summary_text: The compacted summary text.
        heartbeat_sequence: The heartbeat sequence when this was compacted.
        entries_compacted: Number of raw entries compacted.
        timestamp: When the summary was created.
    """

    __tablename__ = "memory_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    heartbeat_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    entries_compacted: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )
