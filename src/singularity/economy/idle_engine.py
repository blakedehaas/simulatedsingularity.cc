import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class DigitalTwinState(BaseModel):
    id: str
    raw_data_harvested: float = 0.0
    simulation_epochs: int = 0
    lvl_keystroke: int = 0
    lvl_semantic: int = 0
    lvl_biometric: int = 0
    lvl_consciousness_rag: int = 0
    data_per_second: float = 0.0

UPGRADE_CONFIGS = {
    "keystroke": {"base_cost": 10.0, "growth_factor": 1.15, "dps_per_level": 1.0},
    "semantic": {"base_cost": 100.0, "growth_factor": 1.15, "dps_per_level": 10.0},
    "biometric": {"base_cost": 1000.0, "growth_factor": 1.15, "dps_per_level": 100.0},
    "consciousness_rag": {"base_cost": 5000.0, "growth_factor": 1.15, "dps_per_level": 500.0}
}

def calculate_upgrade_cost(base_cost: float, growth_factor: float, current_level: int) -> float:
    """Calculate the cost of the next upgrade level."""
    return base_cost * (growth_factor ** current_level)

def calculate_dps(state: DigitalTwinState) -> float:
    """Calculate the total Data Per Second for the digital twin."""
    base_dps = (
        state.lvl_keystroke * UPGRADE_CONFIGS["keystroke"]["dps_per_level"] +
        state.lvl_semantic * UPGRADE_CONFIGS["semantic"]["dps_per_level"] +
        state.lvl_biometric * UPGRADE_CONFIGS["biometric"]["dps_per_level"] +
        state.lvl_consciousness_rag * UPGRADE_CONFIGS["consciousness_rag"]["dps_per_level"]
    )
    prestige_multiplier = 1.0 + (state.simulation_epochs * 0.5)
    return base_dps * prestige_multiplier

def process_idle_tick(state: DigitalTwinState, tick_seconds: int = 60) -> DigitalTwinState:
    """Process an idle tick and add harvested data."""
    logger.debug(f"Processing idle tick for {tick_seconds}s on twin {state.id}")
    
    # Create a copy for pure function behavior
    new_state = state.model_copy()
    
    dps = calculate_dps(new_state)
    new_state.data_per_second = dps
    new_state.raw_data_harvested += dps * tick_seconds
    
    return new_state

def perform_ascension(state: DigitalTwinState) -> DigitalTwinState:
    """Perform a prestige ascension, resetting progress but gaining epochs."""
    logger.info(f"Twin {state.id} performing ascension to epoch {state.simulation_epochs + 1}")
    
    new_state = state.model_copy()
    new_state.raw_data_harvested = 0.0
    new_state.lvl_keystroke = 0
    new_state.lvl_semantic = 0
    new_state.lvl_biometric = 0
    new_state.lvl_consciousness_rag = 0
    new_state.simulation_epochs += 1
    new_state.data_per_second = calculate_dps(new_state)
    
    return new_state
