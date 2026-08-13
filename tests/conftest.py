"""Shared test fixtures for the Simulated Singularity CC test suite.

Provides temporary database fixtures, mock agent instances, and
common utilities used across all test modules.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
import os
from unittest.mock import MagicMock
from typing import AsyncIterator

# Inject a dummy Google API key so agents instantiate without ValidationError
os.environ["GOOGLE_API_KEY"] = "mocked-test-key"

import pytest
import pytest_asyncio

from singularity.neural_core.node_base import (
    CognitiveOutput,
    NodeStatus,
    CognitiveNode,
    SystemPulse,
    C2InterventionRequest,
    ActionProposal,
    SynapticTransmission,
    RiskLevel,
    DiagnosticFrame,
)
from singularity.neural_core.node_registry import reset_registry
from singularity.memory_vault.database import close_database, init_database


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


@pytest_asyncio.fixture(autouse=True)
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

class MockNode(CognitiveNode):
    """Minimal concrete agent for testing the ABC contract."""

    AGENT_ID = "mock-001"

    def __init__(
        self,
        node_id: str = "mock-001",
        node_name: str = "MockNode",
        node_role: str = "Testing",
        priority: int = 99,
        **kwargs: object,
    ) -> None:
        super().__init__(
            node_id=node_id,
            node_name=node_name,
            node_role=node_role,
            priority=priority,
        )
        self._prompt_count = 0
        self._heartbeat_count = 0

    async def handle_prompt(self, payload: SynapticTransmission) -> CognitiveOutput:
        """Process a prompt and return a mock response."""
        self._prompt_count += 1
        return CognitiveOutput(
            node_id=self.node_id,
            content=f"Mock response to: {payload.content}",
            telemetry=await self.emit_telemetry(),
        )

    async def handle_heartbeat(self, heartbeat: SystemPulse) -> DiagnosticFrame:
        """Process a heartbeat and return telemetry."""
        self._heartbeat_count += 1
        return await self.emit_telemetry()

    async def emit_telemetry(self) -> DiagnosticFrame:
        """Emit mock telemetry data."""
        return DiagnosticFrame(
            node_id=self.node_id,
            status=self.status,
            metrics={
                "prompts_processed": float(self._prompt_count),
                "heartbeats_received": float(self._heartbeat_count),
            },
            message="Mock agent operational",
        )


@pytest.fixture
def mock_agent() -> MockNode:
    """Provide a fresh MockNode instance."""
    return MockNode()


@pytest.fixture(autouse=True)
def clean_registry() -> None:
    """Reset the agent registry before each test."""
    reset_registry()


# ---------------------------------------------------------------------------
# Payload fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_prompt_payload() -> SynapticTransmission:
    """Provide a sample prompt payload for testing."""
    return SynapticTransmission(
        source_node_id="ground_control",
        target_node_id="mock-001",
        content="Run a system health check",
    )


@pytest.fixture
def sample_heartbeat() -> SystemPulse:
    """Provide a sample heartbeat event for testing."""
    return SystemPulse(
        sequence_number=1,
        constellation_summary={"mock-001": NodeStatus.NOMINAL},
    )


@pytest.fixture
def sample_proposed_action() -> ActionProposal:
    """Provide a sample proposed action for testing."""
    return ActionProposal(
        node_id="mock-001",
        action_type="tool_call",
        description="Execute system diagnostic scan",
        parameters={"target": "all_nodes", "depth": "full"},
        risk_level=RiskLevel.MEDIUM,
    )

# ---------------------------------------------------------------------------
# API fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_api_client():
    """Create a FastAPI TestClient for the Singularity API."""
    from fastapi.testclient import TestClient
    from singularity.api.app import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# Temporal fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_temporal_vector_memory():
    """Provide a mocked vector memory for temporal RAG testing."""
    mock_memory = MagicMock()
    mock_memory.retrieve_context.return_value = "Sample temporal data for the requested era."
    return mock_memory


# ---------------------------------------------------------------------------
# Economy fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_digital_twin_state():
    """Provide a preset DigitalTwinState instance for testing."""
    from singularity.economy.idle_engine import DigitalTwinState
    return DigitalTwinState(
        id="test-twin-001",
        raw_data_harvested=100.0,
        simulation_epochs=0,
        lvl_keystroke=0,
        lvl_semantic=0,
        lvl_biometric=0,
        lvl_consciousness_rag=0,
        data_per_second=0.0,
    )
