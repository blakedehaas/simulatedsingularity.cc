import logging
import pytest

from singularity.economy.idle_engine import (
    DigitalTwinState,
    calculate_upgrade_cost,
    calculate_dps,
    process_idle_tick,
    perform_ascension,
)

logger = logging.getLogger(__name__)

def test_calculate_upgrade_cost_base_level():
    """TRACE-IDLE-001: Test base cost for level 0 upgrade."""
    logger.debug("Testing calculate_upgrade_cost at base level")
    
    cost = calculate_upgrade_cost(base_cost=10.0, growth_factor=1.15, current_level=0)
    assert cost == 10.0

def test_calculate_upgrade_cost_exponential():
    """TRACE-IDLE-002: Test exponential cost growth at level 10."""
    logger.debug("Testing calculate_upgrade_cost at level 10")
    
    base_cost = 10.0
    growth_factor = 1.15
    level = 10
    
    cost = calculate_upgrade_cost(base_cost, growth_factor, level)
    expected_cost = base_cost * (growth_factor ** level)
    
    assert cost == pytest.approx(expected_cost, rel=1e-5)

def test_calculate_dps_zero_upgrades(sample_digital_twin_state):
    """TRACE-IDLE-003: Test that DPS is 0 when all upgrades are at level 0."""
    logger.debug("Testing calculate_dps with 0 upgrades")
    
    dps = calculate_dps(sample_digital_twin_state)
    assert dps == 0.0

def test_calculate_dps_with_prestige(sample_digital_twin_state):
    """TRACE-IDLE-004: Test DPS calculation when epochs > 0 applies a multiplier."""
    logger.debug("Testing calculate_dps with prestige/epochs")
    
    state = sample_digital_twin_state
    state.lvl_keystroke = 5
    
    base_state = DigitalTwinState(**{**state.model_dump(), "simulation_epochs": 0})
    base_dps = calculate_dps(base_state)
    
    state.simulation_epochs = 2
    prestige_dps = calculate_dps(state)
    
    expected_multiplier = 1.0 + (2 * 0.5)
    assert prestige_dps == base_dps * expected_multiplier

def test_process_idle_tick(sample_digital_twin_state):
    """TRACE-IDLE-005: Test idle tick increases raw data correctly."""
    logger.debug("Testing process_idle_tick")
    
    state = sample_digital_twin_state
    state.lvl_keystroke = 10  # 10 * 1.0 = 10 dps
    initial_data = state.raw_data_harvested
    
    tick_seconds = 60
    new_state = process_idle_tick(state, tick_seconds)
    
    expected_dps = calculate_dps(state)
    assert new_state.raw_data_harvested == initial_data + (expected_dps * 60)

def test_perform_ascension(sample_digital_twin_state):
    """TRACE-IDLE-006: Test ascension resets data and increments epochs."""
    logger.debug("Testing perform_ascension resets")
    
    state = sample_digital_twin_state
    state.raw_data_harvested = 1000.0
    state.lvl_keystroke = 10
    state.lvl_semantic = 5
    state.data_per_second = 50.0
    state.simulation_epochs = 0
    
    ascended_state = perform_ascension(state)
    
    assert ascended_state.raw_data_harvested == 0.0
    assert ascended_state.lvl_keystroke == 0
    assert ascended_state.lvl_semantic == 0
    assert ascended_state.lvl_biometric == 0
    assert ascended_state.lvl_consciousness_rag == 0
    assert ascended_state.simulation_epochs == 1

def test_perform_ascension_preserves_epochs(sample_digital_twin_state):
    """TRACE-IDLE-007: Test multiple ascensions increment epochs correctly."""
    logger.debug("Testing perform_ascension multiple times")
    
    state = sample_digital_twin_state
    state.simulation_epochs = 2
    
    ascended_state = perform_ascension(state)
    assert ascended_state.simulation_epochs == 3
    
    ascended_state2 = perform_ascension(ascended_state)
    assert ascended_state2.simulation_epochs == 4

def test_upgrade_cost_growth():
    """TRACE-IDLE-008: Test upgrade costs strictly increase with level."""
    logger.debug("Testing upgrade cost strictly increases")
    
    base_cost = 10.0
    growth_factor = 1.15
    
    prev_cost = calculate_upgrade_cost(base_cost, growth_factor, 0)
    for level in range(1, 20):
        current_cost = calculate_upgrade_cost(base_cost, growth_factor, level)
        assert current_cost > prev_cost
        prev_cost = current_cost
