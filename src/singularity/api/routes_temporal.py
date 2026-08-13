import logging
from fastapi import APIRouter
from pydantic import BaseModel
from singularity.temporal.temporal_rag import instantiate_temporal_agent, simulate_dialectic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/temporal", tags=["Temporal RAG"])

class DialecticRequest(BaseModel):
    age_a: int
    age_b: int
    topic: str = "the nature of our past decisions"

@router.post("/dialectic")
async def run_dialectic(payload: DialecticRequest) -> dict:
    """Run a dialectic between two temporal fragments."""
    logger.info(f"Running dialectic between {payload.age_a} and {payload.age_b}")
    agent_a = instantiate_temporal_agent(payload.age_a, 2000)
    agent_b = instantiate_temporal_agent(payload.age_b, 2000)
    dialogue = await simulate_dialectic(agent_a, agent_b, payload.topic)
    return {"dialogue": dialogue}
