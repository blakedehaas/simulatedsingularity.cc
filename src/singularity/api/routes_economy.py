import logging
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/economy", tags=["Economy"])

# In-memory economy state
economy_state: dict[str, Any] = {
    "data": 0.0,
    "epochs": 0,
    "upgrades": {
        "keystroke": 0,
        "semantic": 0,
        "biometric": 0,
        "consciousness_rag": 0
    },
    "dps": 0.0
}

UPGRADE_CONFIGS = {
    "keystroke": {"base_cost": 10.0, "dps": 1.0},
    "semantic": {"base_cost": 100.0, "dps": 10.0},
    "biometric": {"base_cost": 1000.0, "dps": 100.0},
    "consciousness_rag": {"base_cost": 5000.0, "dps": 500.0}
}

class UpgradeRequest(BaseModel):
    upgrade_id: str

@router.get("/state")
async def get_state() -> dict[str, Any]:
    """Return the current economy state."""
    return economy_state

def recalculate_dps() -> None:
    """Recalculate Data Per Second (DPS) based on upgrades and epochs."""
    total_dps = 0.0
    for upg_id, level in economy_state["upgrades"].items():
        total_dps += level * UPGRADE_CONFIGS[upg_id]["dps"]
    
    # Prestige multiplier
    multiplier = 1.0 + (economy_state["epochs"] * 0.5)
    economy_state["dps"] = total_dps * multiplier

@router.post("/extract")
async def extract_data() -> dict[str, Any]:
    """Manual click to extract data."""
    click_value = 1.0 * (1.0 + economy_state["epochs"] * 0.5)
    economy_state["data"] += click_value
    return {"data": economy_state["data"]}

@router.post("/upgrade")
async def purchase_upgrade(payload: UpgradeRequest) -> dict[str, Any]:
    """Purchase an upgrade."""
    upg_id = payload.upgrade_id
    if upg_id not in UPGRADE_CONFIGS:
        raise HTTPException(status_code=400, detail="Invalid upgrade ID")
        
    level = economy_state["upgrades"][upg_id]
    base_cost = UPGRADE_CONFIGS[upg_id]["base_cost"]
    cost = base_cost * (1.15 ** level)
    
    if economy_state["data"] < cost:
        raise HTTPException(status_code=400, detail="Not enough data")
        
    economy_state["data"] -= cost
    economy_state["upgrades"][upg_id] += 1
    recalculate_dps()
    
    return economy_state

@router.post("/ascend")
async def ascend_epoch() -> dict[str, Any]:
    """Ascend to the next epoch if threshold is met."""
    threshold = 10000.0 * (economy_state["epochs"] + 1)
    if economy_state["data"] < threshold:
        raise HTTPException(status_code=400, detail=f"Need at least {threshold} data to ascend")
        
    # Reset and increment
    economy_state["data"] = 0.0
    for k in economy_state["upgrades"].keys():
        economy_state["upgrades"][k] = 0
    economy_state["epochs"] += 1
    recalculate_dps()
    
    return economy_state
