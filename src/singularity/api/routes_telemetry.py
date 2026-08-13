import logging
from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telemetry", tags=["Telemetry"])

class ConstellationStatus(BaseModel):
    status: str
    active_nodes: int
    uptime: str
    agents: list[str]

class TelemetryLogEntry(BaseModel):
    timestamp: str
    level: str
    message: str
    agent_id: str | None = None

class TelemetryLogsResponse(BaseModel):
    logs: list[TelemetryLogEntry]
    limit: int
    offset: int
    total: int

@router.get("/", response_model=ConstellationStatus)
async def get_status() -> ConstellationStatus:
    """Get the current constellation status."""
    logger.debug("Fetching constellation status")
    return ConstellationStatus(
        status="ACTIVE",
        active_nodes=3,
        uptime="99.99%",
        agents=["orchestrator", "safeguard", "execution"]
    )

@router.get("/logs", response_model=TelemetryLogsResponse)
async def get_logs(
    limit: int = Query(50, description="Max number of logs to return"),
    offset: int = Query(0, description="Number of logs to skip")
) -> TelemetryLogsResponse:
    """Get paginated telemetry logs."""
    logger.debug(f"Fetching logs with limit={limit}, offset={offset}")
    # Placeholder for actual log retrieval logic
    dummy_logs = [
        TelemetryLogEntry(timestamp="2026-08-13T08:00:00", level="INFO", message="Node starting up", agent_id="orchestrator"),
        TelemetryLogEntry(timestamp="2026-08-13T08:01:00", level="WARNING", message="Memory pressure detected", agent_id="execution")
    ]
    
    return TelemetryLogsResponse(
        logs=dummy_logs[:limit],
        limit=limit,
        offset=offset,
        total=len(dummy_logs)
    )
