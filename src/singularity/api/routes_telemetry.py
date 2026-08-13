import logging
import json
from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy.future import select

from singularity.persistence.database import get_session
from singularity.persistence.models import SimulationMessage

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

@router.get("/")
async def get_global_telemetry() -> list[dict]:
    """Get the global telemetry stream (latest simulation messages)."""
    logger.debug("Fetching global telemetry")
    async with get_session() as db:
        result = await db.execute(
            select(SimulationMessage)
            .order_by(SimulationMessage.timestamp.desc())
            .limit(50)
        )
        messages = result.scalars().all()
        
    logs = []
    for m in messages:
        text = m.content
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list) and len(parsed) > 0 and "text" in parsed[0]:
                text = parsed[0]["text"]
        except Exception:
            pass
            
        logs.append({
            "id": str(m.id),
            "agent": m.sender,
            "message": text,
            "timestamp": m.timestamp.isoformat() if m.timestamp else None
        })
    return logs

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
