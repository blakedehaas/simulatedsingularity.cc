import logging
import asyncio
from typing import Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from pydantic import BaseModel
from singularity.orchestration.evolutionary_engine import mutate_topology
from singularity.orchestration.swarm_state import SwarmState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vr", tags=["VR Sandbox"])

# In-memory universe state
universe_state: dict[str, Any] = {
    "voxels": {},
    "agents": {
        "execution_node": {
            "position": [0, 1.5, -5],
            "scratchpad": "Awaiting instructions...",
            "color": "#06b6d4"
        }
    }
}

# In-memory global swarm topology state for API serving
swarm_topology_state: dict[str, Any] = {
    "adjacency_matrix": {}
}

@router.get("/state")
async def get_state() -> dict[str, Any]:
    """Return the current universe state snapshot."""
    return universe_state

from singularity.orchestration.social_dynamics import detect_clusters, assign_hierarchy

@router.get("/swarm")
async def get_swarm_topology() -> dict[str, Any]:
    """Return the current n-dimensional swarm adjacency matrix, along with clusters and leaders."""
    state_obj = SwarmState(
        messages=[],
        active_agents=["execution_node", "safeguard", "orchestrator"],
        adjacency_matrix=swarm_topology_state.get("adjacency_matrix", {})
    )
    
    clusters = detect_clusters(state_obj)
    leaders = assign_hierarchy(state_obj, clusters)
    
    # Format clusters for JSON serialization (sets to lists)
    swarm_topology_state["clusters"] = [list(c) for c in clusters]
    swarm_topology_state["leaders"] = leaders
    
    return swarm_topology_state

class MutateRequest(BaseModel):
    feedback_reward: float
    source: str
    target: str

@router.post("/swarm/mutate")
async def mutate_swarm_topology(request: MutateRequest) -> dict[str, Any]:
    """Manually trigger a mutation on the swarm topology."""
    global swarm_topology_state
    
    # Convert dict to SwarmState for mutation
    state_obj = SwarmState(
        messages=[],
        active_agents=["execution_node", request.source, request.target],
        adjacency_matrix=swarm_topology_state.get("adjacency_matrix", {})
    )
    
    new_state = mutate_topology(
        state=state_obj, 
        feedback_reward=request.feedback_reward, 
        source=request.source, 
        target=request.target
    )
    
    # Update global dict
    swarm_topology_state["adjacency_matrix"] = new_state.adjacency_matrix
    
    return swarm_topology_state

@router.websocket("/sync")
async def websocket_sync(websocket: WebSocket) -> None:
    """Sync the universe state with a client via WebSocket."""
    await websocket.accept()
    logger.info("VR client connected")
    try:
        while True:
            # Send current state
            await websocket.send_json(universe_state)
            
            # Non-blocking receive (with a timeout in real usage, but we simplify here)
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=0.01)
                action = data.get("action")
                payload = data.get("payload", {})
                
                if action == "DESTROY_BLOCK":
                    block_id = payload.get("id")
                    if block_id in universe_state["voxels"]:
                        del universe_state["voxels"][block_id]
                elif action == "MOVE_AGENT":
                    agent_id = payload.get("agent_id")
                    position = payload.get("position")
                    if agent_id in universe_state["agents"]:
                        universe_state["agents"][agent_id]["position"] = position
                        
            except asyncio.TimeoutError:
                pass # Just keep sending state
            
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        logger.info("VR client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
