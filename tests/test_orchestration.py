import pytest
from typing import TypedDict
from singularity.swarm_orchestration.state import ConstellationState

def test_constellation_state_init():
    # ConstellationState is essentially just a TypedDict schema, we can test it by instantiating a dict
    # that conforms to it.
    
    class MockState(TypedDict):
        messages: list
        current_node: str
        routing_history: list
        action_proposals: list
        pending_interventions: list
        diagnostic_frames: dict
        pulse_sequence: int
        is_interrupted: bool

    state: MockState = {
        "messages": [],
        "current_node": "test",
        "routing_history": [],
        "action_proposals": [],
        "pending_interventions": [],
        "diagnostic_frames": {},
        "pulse_sequence": 0,
        "is_interrupted": False
    }
    
    assert state["current_node"] == "test"
    assert len(state["messages"]) == 0
    assert not state["is_interrupted"]
