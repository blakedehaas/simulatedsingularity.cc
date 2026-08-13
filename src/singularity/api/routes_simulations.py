import logging
import uuid
import datetime
from typing import Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.future import select

from singularity.persistence.database import get_session
from singularity.persistence.models import (
    SimulationSession,
    SimulationMessage,
    LanguageSimulationConfig
)
from singularity.core.language_simulation import run_simulation_loop

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/simulations", tags=["Simulations"])

class SpawnRequest(BaseModel):
    name: str
    seed: int

class LanguageSpawnRequest(BaseModel):
    name: str
    seed: int
    seed_prompt: str
    end_state_condition: str
    agents_config: list[dict[str, Any]]
    verbose_mode: bool = False
    max_tokens: int | None = None

class ImportRequest(BaseModel):
    version: str
    simulation: dict[str, Any]
    history: list[dict[str, Any]]



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
    
    async with get_session() as db:
        session = SimulationSession(
            id=sim_id,
            name=request.name,
            seed=request.seed,
            topology_snapshot=snapshot
        )
        db.add(session)
    
    sim_data = {
        "id": sim_id,
        "name": request.name,
        "seed": request.seed,
        "topology_snapshot": snapshot,
    }
    
    return sim_data

@router.get("/library")
async def list_simulations() -> list[dict[str, Any]]:
    """Return a list of all saved simulations."""
    async with get_session() as db:
        result = await db.execute(select(SimulationSession))
        sessions = result.scalars().all()
        
    return [
        {
            "id": s.id,
            "name": s.name,
            "seed": s.seed,
            "topology_snapshot": s.topology_snapshot,
            "created_at": s.created_at.isoformat() if s.created_at else None
        }
        for s in sessions
    ]

@router.post("/{sim_id}/reboot")
async def reboot_simulation(sim_id: str) -> dict[str, Any]:
    """Load a saved topology_snapshot into the active orchestrator."""
    async with get_session() as db:
        result = await db.execute(select(SimulationSession).where(SimulationSession.id == sim_id))
        sim_data = result.scalars().first()
        
    if not sim_data:
        raise HTTPException(status_code=404, detail="Simulation not found")
        
    # Inject into global active orchestrator state (routes_sandbox handles UI state)
    from singularity.api.routes_sandbox import swarm_topology_state
    
    swarm_topology_state["adjacency_matrix"] = sim_data.topology_snapshot.get("adjacency_matrix", {})
    
    logger.info(f"Rebooted simulation {sim_id} into active orchestrator")
    return {"status": "success", "message": f"Simulation {sim_data.name} loaded"}

@router.get("/{sim_id}/messages")
async def get_simulation_messages(sim_id: str) -> list[dict[str, Any]]:
    """Return the chronological chat log for the session."""
    async with get_session() as db:
        result = await db.execute(
            select(SimulationMessage)
            .where(SimulationMessage.session_id == sim_id)
            .order_by(SimulationMessage.timestamp)
        )
        messages = result.scalars().all()
        
    return [
        {
            "sender": m.sender,
            "content": m.content,
            "timestamp": m.timestamp.isoformat() if m.timestamp else None
        }
        for m in messages
    ]

@router.get("/{sim_id}/export")
async def export_simulation(sim_id: str) -> dict[str, Any]:
    """Export the entire simulation state to a JSON object."""
    async with get_session() as db:
        result = await db.execute(select(SimulationSession).where(SimulationSession.id == sim_id))
        session = result.scalars().first()
        if not session:
            raise HTTPException(status_code=404, detail="Simulation not found")
            
        result_config = await db.execute(select(LanguageSimulationConfig).where(LanguageSimulationConfig.session_id == sim_id))
        config = result_config.scalars().first()
        
        result_msgs = await db.execute(
            select(SimulationMessage)
            .where(SimulationMessage.session_id == sim_id)
            .order_by(SimulationMessage.timestamp)
        )
        messages = result_msgs.scalars().all()
        
    history = [
        {
            "sender": msg.sender,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
        }
        for msg in messages
    ]
    
    export_data = {
        "version": "1.0",
        "simulation": {
            "name": f"Export of {session.name}",
            "verbose_mode": getattr(config, 'verbose_mode', False) if config else False,
            "max_tokens": getattr(config, 'max_tokens', None) if config else None,
            "seed_prompt": config.seed_prompt if config else "",
            "end_state_condition": config.end_state_condition if config else "",
            "agents_config": config.agents_config if config else []
        },
        "history": history
    }
    
    return export_data

@router.post("/import")
async def import_simulation(request: ImportRequest) -> dict[str, Any]:
    """Import a simulation from a JSON state object."""
    sim_id = str(uuid.uuid4())
    logger.info(f"Importing simulation {sim_id}")
    
    sim_data = request.simulation
    agents_config = sim_data.get("agents_config", [])
    
    snapshot = {
        "active_agents": [agent.get("name") for agent in agents_config]
    }
    
    async with get_session() as db:
        session = SimulationSession(
            id=sim_id,
            name=sim_data.get("name", f"Imported Sim {sim_id[:8]}"),
            seed=42,
            topology_snapshot=snapshot
        )
        
        config = LanguageSimulationConfig(
            id=str(uuid.uuid4()),
            session_id=sim_id,
            seed_prompt=sim_data.get("seed_prompt", ""),
            end_state_condition=sim_data.get("end_state_condition", ""),
            agents_config=agents_config,
            verbose_mode=sim_data.get("verbose_mode", False),
            max_tokens=sim_data.get("max_tokens", None)
        )
        
        db.add(session)
        db.add(config)
        
        for msg_data in request.history:
            new_msg = SimulationMessage(
                session_id=sim_id,
                sender=msg_data.get("sender", "unknown"),
                content=msg_data.get("content", "")
            )
            db.add(new_msg)
            
    return {"status": "Imported", "sim_id": sim_id}

@router.post("/language/spawn")
async def spawn_language_simulation(request: LanguageSpawnRequest) -> dict[str, Any]:
    """Create a new language-based simulation session and configuration."""
    sim_id = str(uuid.uuid4())
    logger.info(f"Spawning language simulation {request.name} (seed {request.seed})")
    
    snapshot = {
        "active_agents": [agent.get("name") for agent in request.agents_config]
    }
    
    async with get_session() as db:
        session = SimulationSession(
            id=sim_id,
            name=request.name,
            seed=request.seed,
            topology_snapshot=snapshot
        )
        
        config = LanguageSimulationConfig(
            id=str(uuid.uuid4()),
            session_id=sim_id,
            seed_prompt=request.seed_prompt,
            end_state_condition=request.end_state_condition,
            agents_config=request.agents_config,
            verbose_mode=request.verbose_mode,
            max_tokens=request.max_tokens
        )
        
        db.add(session)
        db.add(config)
        
    return {
        "id": sim_id,
        "name": request.name,
        "seed": request.seed,
        "topology_snapshot": snapshot,
    }

@router.post("/{sim_id}/start")
async def start_language_simulation(sim_id: str, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Start the language simulation loop in the background."""
    async with get_session() as db:
        result = await db.execute(
            select(LanguageSimulationConfig).where(LanguageSimulationConfig.session_id == sim_id)
        )
        config = result.scalars().first()
        
    if not config:
        raise HTTPException(status_code=404, detail="Language simulation config not found for this session")
        
    # We must detach the config instance from the session before passing it to the background task, 
    # or just use its attributes, as the db session will close. 
    # A cleaner way is to load it into memory eagerly or expunge it.
    db.expunge(config)
        
    background_tasks.add_task(run_simulation_loop, sim_id, config)
    
    return {"status": "started", "sim_id": sim_id}

@router.post("/{sim_id}/kill")
async def kill_simulation(sim_id: str) -> dict[str, Any]:
    """Signal the active simulation loop to terminate."""
    from singularity.core.language_simulation import active_shutdown_signals
    active_shutdown_signals.add(sim_id)
    logger.info(f"Received kill signal for session {sim_id}")
    return {"status": "kill_signal_sent", "sim_id": sim_id}
