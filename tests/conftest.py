"""Shared test fixtures for the Simulated Singularity CC test suite.

Provides temporary database fixtures, mock agent instances, and
common utilities used across all test modules.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncIterator

import pytest
import pytest_asyncio

from singularity.core.agent_base import (
    AgentResponse,
    AgentStatus,
    AsyncBaseAgent,
    HeartbeatEvent,
    InterruptRequest,
    ProposedAction,
    PromptPayload,
    RiskLevel,
    TelemetryFrame,
)
from singularity.core.agent_registry import reset_registry
from singularity.persistence.database import close_database, init_database


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def temp_db_path(tmp_path: Path) -> Path:
    """Provide a temporary database file path.

    Returns:
        Path to a temporary SQLite database file.
    """
    return tmp_path / "test_singularity.db"


@pytest_asyncio.fixture
async def initialized_db(temp_db_path: Path) -> AsyncIterator[Path]:
    """Initialize a temporary database and tear it down after the test.

    Yields:
        Path to the initialized temporary database.
    """
    await init_database(db_path=temp_db_path)
    yield temp_db_path
    await close_database()


# ---------------------------------------------------------------------------
# Agent fixtures
# ---------------------------------------------------------------------------

class MockAgent(AsyncBaseAgent):
    """Minimal concrete agent for testing the ABC contract."""

    AGENT_ID = "mock-001"

    def __init__(
        self,
        agent_id: str = "mock-001",
        agent_name: str = "MockAgent",
        agent_role: str = "Testing",
        priority: int = 99,
        **kwargs: object,
    ) -> None:
        super().__init__(
            agent_id=agent_id,
            agent_name=agent_name,
            agent_role=agent_role,
            priority=priority,
        )
        self._prompt_count = 0
        self._heartbeat_count = 0

    async def receive_prompt(self, payload: PromptPayload) -> AgentResponse:
        """Process a prompt and return a mock response."""
        self._prompt_count += 1
        return AgentResponse(
            agent_id=self.agent_id,
            content=f"Mock response to: {payload.content}",
            telemetry=await self.emit_telemetry(),
        )

    async def process_heartbeat(self, heartbeat: HeartbeatEvent) -> TelemetryFrame:
        """Process a heartbeat and return telemetry."""
        self._heartbeat_count += 1
        return await self.emit_telemetry()

    async def emit_telemetry(self) -> TelemetryFrame:
        """Emit mock telemetry data."""
        return TelemetryFrame(
            agent_id=self.agent_id,
            status=self.status,
            metrics={
                "prompts_processed": float(self._prompt_count),
                "heartbeats_received": float(self._heartbeat_count),
            },
            message="Mock agent operational",
        )


@pytest.fixture
def mock_agent() -> MockAgent:
    """Provide a fresh MockAgent instance."""
    return MockAgent()


@pytest.fixture(autouse=True)
def clean_registry() -> None:
    """Reset the agent registry before each test."""
    reset_registry()


# ---------------------------------------------------------------------------
# Payload fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_prompt_payload() -> PromptPayload:
    """Provide a sample prompt payload for testing."""
    return PromptPayload(
        source_agent_id="ground_control",
        target_agent_id="mock-001",
        content="Run a system health check",
    )


@pytest.fixture
def sample_heartbeat() -> HeartbeatEvent:
    """Provide a sample heartbeat event for testing."""
    return HeartbeatEvent(
        sequence_number=1,
        constellation_summary={"mock-001": AgentStatus.NOMINAL},
    )


@pytest.fixture
def sample_proposed_action() -> ProposedAction:
    """Provide a sample proposed action for testing."""
    return ProposedAction(
        agent_id="mock-001",
        action_type="tool_call",
        description="Execute system diagnostic scan",
        parameters={"target": "all_nodes", "depth": "full"},
        risk_level=RiskLevel.MEDIUM,
    )
