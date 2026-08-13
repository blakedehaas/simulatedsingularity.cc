import logging
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/console", tags=["Console"])

class ResolveRequest(BaseModel):
    action: str
    agent_id: str | None = None
    override_prompt: str | None = None
    session_id: str | None = None

class ResolveResponse(BaseModel):
    status: str
    action: str

active_intercepts = {}

@router.get("/intercepts")
async def get_intercepts() -> dict:
    """Get all active intercepts that require human approval."""
    return active_intercepts

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
    logger.info(f"C2 decision logged: {payload.action}")
    
    # If session_id is provided, resolve that specific session
    if payload.session_id and payload.session_id in active_intercepts:
        active_intercepts[payload.session_id]["decision"] = payload.action
        active_intercepts[payload.session_id]["resolved"] = True
    else:
        # Otherwise resolve all active intercepts (fallback for global UI)
        for sid in active_intercepts:
            active_intercepts[sid]["decision"] = payload.action
            active_intercepts[sid]["resolved"] = True
            
    return ResolveResponse(
        status="State Resumed",
        action=payload.action
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
