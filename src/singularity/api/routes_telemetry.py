import logging
import json
from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy.future import select

from singularity.memory_vault.database import get_session
from singularity.memory_vault.models import SimulationMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telemetry", tags=["Telemetry"])

class ConstellationStatus(BaseModel):
    status: str
    active_nodes: int
    uptime: str
    agents: list[str]

class DiagnosticLogEntry(BaseModel):
    timestamp: str
    level: str
    message: str
    node_id: str | None = None

class DiagnosticLogsResponse(BaseModel):
    logs: list[DiagnosticLogEntry]
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

@router.get("/logs", response_model=DiagnosticLogsResponse)
async def get_logs(
    limit: int = Query(50, description="Max number of logs to return"),
    offset: int = Query(0, description="Number of logs to skip")
) -> DiagnosticLogsResponse:
    """Get paginated telemetry logs."""
    logger.debug(f"Fetching logs with limit={limit}, offset={offset}")
    return DiagnosticLogsResponse(
        logs=[],
        limit=limit,
        offset=offset,
        total=0
    )
