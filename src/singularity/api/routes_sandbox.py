import logging
import asyncio
from typing import Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

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

@router.get("/state")
async def get_state() -> dict[str, Any]:
    """Return the current universe state snapshot."""
    return universe_state

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
