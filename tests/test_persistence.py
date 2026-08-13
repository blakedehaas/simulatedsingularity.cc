"""Tests for the persistence layer — database, ORM models, and repositories."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
import pytest_asyncio

from singularity.memory_vault.database import get_session, init_database, close_database
from singularity.memory_vault.models import (
    NodeMemoryRecord,
    NodeProfileRecord,
    CommunicationLogRecord,
    ExecutionStateRecord,
    ScheduledTaskRecord,
    SyncPromptRecord,
)
from singularity.memory_vault.repository import (
    NodeRepository,
    LogRepository,
    StateRepository,
    TaskRepository,
)


# ---------------------------------------------------------------------------
# Database engine tests
# ---------------------------------------------------------------------------

class TestDatabaseEngine:
    """Tests for database initialization and session management."""

    @pytest.mark.asyncio
    async def test_init_creates_tables(self, temp_db_path: Path) -> None:
        """init_database should create the SQLite file and all tables."""
        engine = await init_database(db_path=temp_db_path)
        assert temp_db_path.exists()
        await close_database()

    @pytest.mark.asyncio
    async def test_session_auto_commit(self, initialized_db: Path) -> None:
        """Session should auto-commit on clean exit."""
        async with get_session() as session:
            record = NodeProfileRecord(
                node_id="test-agent",
                name="TestNode",
                role="Testing",
            )
            session.add(record)

        # Verify the record was committed
        async with get_session() as session:
            result = await session.get(NodeProfileRecord, "test-agent")
            assert result is not None
            assert result.name == "TestNode"

    @pytest.mark.asyncio
    async def test_session_rollback_on_error(self, initialized_db: Path) -> None:
        """Session should rollback on exception."""
        try:
            async with get_session() as session:
                record = NodeProfileRecord(
                    node_id="rollback-test",
                    name="RollbackNode",
                    role="Testing",
                )
                session.add(record)
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Verify the record was NOT committed
        async with get_session() as session:
            result = await session.get(NodeProfileRecord, "rollback-test")
            assert result is None

    @pytest.mark.asyncio
    async def test_session_without_init_raises(self) -> None:
        """get_session should raise if database not initialized."""
        await close_database()
        with pytest.raises(RuntimeError, match="not initialized"):
            async with get_session():
                pass


# ---------------------------------------------------------------------------
# Agent Repository tests
# ---------------------------------------------------------------------------

class TestAgentRepository:
    """Tests for agent profile and memory CRUD operations."""

    @pytest.mark.asyncio
    async def test_upsert_creates_profile(self, initialized_db: Path) -> None:
        """upsert_profile should create a new profile."""
        record = await NodeRepository.upsert_profile(
            node_id="sec-001",
            name="FirewallNode",
            role="Apex Admin",
            system_prompt="You are the security agent.",
            priority=0,
        )
        assert record.node_id == "sec-001"
        assert record.name == "FirewallNode"
        assert record.priority == 0

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, initialized_db: Path) -> None:
        """upsert_profile should update an existing profile."""
        await NodeRepository.upsert_profile(
            node_id="sec-001",
            name="FirewallNode",
            role="Apex Admin",
        )
        updated = await NodeRepository.upsert_profile(
            node_id="sec-001",
            name="SecurityAgentV2",
            role="Apex Admin Enhanced",
        )
        assert updated.name == "SecurityAgentV2"

    @pytest.mark.asyncio
    async def test_get_profile(self, initialized_db: Path) -> None:
        """get_profile should retrieve by ID."""
        await NodeRepository.upsert_profile(
            node_id="core-001", name="NexusNode", role="Operator"
        )
        profile = await NodeRepository.get_profile("core-001")
        assert profile is not None
        assert profile.name == "NexusNode"

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, initialized_db: Path) -> None:
        """get_profile should return None for unknown ID."""
        profile = await NodeRepository.get_profile("nonexistent")
        assert profile is None

    @pytest.mark.asyncio
    async def test_get_all_profiles_ordered(self, initialized_db: Path) -> None:
        """get_all_profiles should return profiles ordered by priority."""
        await NodeRepository.upsert_profile("b", "B", "Role", priority=10)
        await NodeRepository.upsert_profile("a", "A", "Role", priority=1)
        await NodeRepository.upsert_profile("c", "C", "Role", priority=5)

        profiles = await NodeRepository.get_all_profiles()
        priorities = [p.priority for p in profiles]
        assert priorities == sorted(priorities)

    @pytest.mark.asyncio
    async def test_save_and_get_memories(self, initialized_db: Path) -> None:
        """save_memory and get_memories should round-trip correctly."""
        # Must create profile first (FK constraint)
        await NodeRepository.upsert_profile("mem-001", "Memory", "DB Controller")
        await NodeRepository.save_memory("mem-001", "input1", "output1")
        await NodeRepository.save_memory("mem-001", "input2", "output2")

        memories = await NodeRepository.get_memories("mem-001")
        assert len(memories) == 2
        # Most recent first
        assert memories[0].input_text == "input2"


# ---------------------------------------------------------------------------
# Task Repository tests
# ---------------------------------------------------------------------------

class TestTaskRepository:
    """Tests for scheduled task CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_task(self, initialized_db: Path) -> None:
        """create_task should persist a new task."""
        task = await TaskRepository.create_task(
            target_node="sec-001",
            prompt_text="Run security scan",
            execute_at=datetime.now(timezone.utc) + timedelta(seconds=60),
        )
        assert task.task_id
        assert task.status == "pending"

    @pytest.mark.asyncio
    async def test_get_pending_tasks(self, initialized_db: Path) -> None:
        """get_pending_tasks should return only pending tasks."""
        await TaskRepository.create_task(
            "a", "prompt1", datetime.now(timezone.utc)
        )
        await TaskRepository.create_task(
            "b", "prompt2", datetime.now(timezone.utc)
        )
        pending = await TaskRepository.get_pending_tasks()
        assert len(pending) == 2

    @pytest.mark.asyncio
    async def test_update_task_status(self, initialized_db: Path) -> None:
        """update_task_status should change status and set result."""
        task = await TaskRepository.create_task(
            "a", "prompt", datetime.now(timezone.utc)
        )
        await TaskRepository.update_task_status(
            task.task_id, "completed", "Success"
        )
        updated = await TaskRepository.get_task(task.task_id)
        assert updated is not None
        assert updated.status == "completed"
        assert updated.result == "Success"

    @pytest.mark.asyncio
    async def test_delete_task(self, initialized_db: Path) -> None:
        """delete_task should remove the task."""
        task = await TaskRepository.create_task(
            "a", "prompt", datetime.now(timezone.utc)
        )
        await TaskRepository.delete_task(task.task_id)
        deleted = await TaskRepository.get_task(task.task_id)
        assert deleted is None


# ---------------------------------------------------------------------------
# Log Repository tests
# ---------------------------------------------------------------------------

class TestLogRepository:
    """Tests for the communication audit log."""

    @pytest.mark.asyncio
    async def test_log_communication(self, initialized_db: Path) -> None:
        """log_communication should persist a log entry."""
        record = await LogRepository.log_communication(
            sender="agent-a",
            recipient="agent-b",
            message="Hello from A",
        )
        assert record.sender == "agent-a"

    @pytest.mark.asyncio
    async def test_get_recent_logs(self, initialized_db: Path) -> None:
        """get_recent_logs should return entries in reverse chronological order."""
        await LogRepository.log_communication("a", "b", "msg1")
        await LogRepository.log_communication("b", "a", "msg2")

        logs = await LogRepository.get_recent_logs(limit=10)
        assert len(logs) == 2

    @pytest.mark.asyncio
    async def test_clear_logs(self, initialized_db: Path) -> None:
        """clear_logs should delete all log entries."""
        await LogRepository.log_communication("a", "b", "msg")
        count = await LogRepository.clear_logs()
        assert count >= 1

        logs = await LogRepository.get_recent_logs()
        assert len(logs) == 0


# ---------------------------------------------------------------------------
# State Repository tests
# ---------------------------------------------------------------------------

class TestStateRepository:
    """Tests for execution state and sync prompt management."""

    @pytest.mark.asyncio
    async def test_save_and_get_state(self, initialized_db: Path) -> None:
        """save_state and get_state should round-trip correctly."""
        state = await StateRepository.save_state(
            graph_run_id="run-123",
            state_json={"messages": [], "current_node": "sec-001"},
        )
        assert state.status == "paused"

        retrieved = await StateRepository.get_state(state.state_id)
        assert retrieved is not None
        assert retrieved.graph_run_id == "run-123"
        assert retrieved.state_json["current_node"] == "sec-001"

    @pytest.mark.asyncio
    async def test_resolve_state(self, initialized_db: Path) -> None:
        """resolve_state should mark state as resumed."""
        state = await StateRepository.save_state("run-1", {"key": "val"})
        await StateRepository.resolve_state(state.state_id, "resumed")

        updated = await StateRepository.get_state(state.state_id)
        assert updated is not None
        assert updated.status == "resumed"
        assert updated.resolved_at is not None

    @pytest.mark.asyncio
    async def test_create_and_query_sync_prompts(
        self, initialized_db: Path
    ) -> None:
        """Sync prompt lifecycle: create → query pending → resolve."""
        state = await StateRepository.save_state("run-2", {})

        prompt = await StateRepository.create_sync_prompt(
            state_id=state.state_id,
            action_type="tool_call",
            description="Execute system scan",
            risk_level="high",
        )
        assert prompt.resolution == "pending"

        pending = await StateRepository.get_pending_sync_prompts()
        assert len(pending) == 1

        await StateRepository.resolve_sync_prompt(
            prompt_id=prompt.prompt_id,
            resolution="approved",
            resolved_by="operator-001",
        )

        pending_after = await StateRepository.get_pending_sync_prompts()
        assert len(pending_after) == 0
