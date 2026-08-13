import logging
import uuid
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/simulations", tags=["Simulations"])

class SpawnRequest(BaseModel):
    name: str
    seed: int

# Mock database for the API layer
_mock_simulations_db: dict[str, dict[str, Any]] = {}
_mock_messages_db: dict[str, list[dict[str, Any]]] = {}

def log_simulation_message(sim_id: str, sender: str, content: str) -> None:
    """Log a new message to the simulation session."""
    import datetime
    if sim_id not in _mock_messages_db:
        _mock_messages_db[sim_id] = []
        
    _mock_messages_db[sim_id].append({
        "sender": sender,
        "content": content,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })

@router.post("/spawn")
async def spawn_simulation(request: SpawnRequest) -> dict[str, Any]:
    """Create a new simulation session."""
    sim_id = str(uuid.uuid4())
    logger.info(f"Spawning simulation {request.name} (seed {request.seed})")
    
    # Mock topology based on seed
    snapshot = {
        "adjacency_matrix": {
            "execution_node": {"safeguard": 0.8},
            "safeguard": {"orchestrator": 0.6}
        },
        "active_agents": ["execution_node", "safeguard", "orchestrator"]
    }
    
    sim_data = {
        "id": sim_id,
        "name": request.name,
        "seed": request.seed,
        "topology_snapshot": snapshot,
        "created_at": "2026-08-13T12:00:00Z"
    }
    
    _mock_simulations_db[sim_id] = sim_data
    return sim_data

@router.get("/library")
async def list_simulations() -> list[dict[str, Any]]:
    """Return a list of all saved simulations."""
    return list(_mock_simulations_db.values())

@router.post("/{sim_id}/reboot")
async def reboot_simulation(sim_id: str) -> dict[str, Any]:
    """Load a saved topology_snapshot into the active orchestrator."""
    if sim_id not in _mock_simulations_db:
        raise HTTPException(status_code=404, detail="Simulation not found")
        
    sim_data = _mock_simulations_db[sim_id]
    
    # Inject into global active orchestrator state (routes_sandbox handles UI state)
    from singularity.api.routes_sandbox import swarm_topology_state
    
    swarm_topology_state["adjacency_matrix"] = sim_data["topology_snapshot"].get("adjacency_matrix", {})
    
    logger.info(f"Rebooted simulation {sim_id} into active orchestrator")
    return {"status": "success", "message": f"Simulation {sim_data['name']} loaded"}

@router.get("/{sim_id}/messages")
async def get_simulation_messages(sim_id: str) -> list[dict[str, Any]]:
    """Return the chronological chat log for the session."""
    if sim_id not in _mock_simulations_db:
        raise HTTPException(status_code=404, detail="Simulation not found")
        
    return _mock_messages_db.get(sim_id, [])
