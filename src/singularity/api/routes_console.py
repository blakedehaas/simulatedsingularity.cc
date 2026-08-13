import logging
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/console", tags=["Console"])

class ResolveRequest(BaseModel):
    decision: str
    agent_id: str
    override_prompt: str

class ResolveResponse(BaseModel):
    status: str
    action: str

class DispatchRequest(BaseModel):
    prompt: str
    target: str

class DispatchResponse(BaseModel):
    status: str
    target: str
    prompt: str

@router.post("/resolve", response_model=ResolveResponse)
async def resolve_decision(payload: ResolveRequest) -> ResolveResponse:
    """Resolve an agent's interrupted state by providing a decision."""
    logger.info(f"C2 decision logged: {payload.decision} for agent {payload.agent_id}")
    return ResolveResponse(
        status="State Resumed",
        action=payload.decision
    )

@router.post("/dispatch", response_model=DispatchResponse)
async def dispatch_task(payload: DispatchRequest) -> DispatchResponse:
    """Dispatch a new prompt/task to a target agent."""
    logger.info(f"Dispatching task to {payload.target}: {payload.prompt[:50]}...")
    return DispatchResponse(
        status="Dispatched",
        target=payload.target,
        prompt=payload.prompt
    )
