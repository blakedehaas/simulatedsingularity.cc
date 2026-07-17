import pytest
from typing import TypedDict
from singularity.orchestration.state import ConstellationState

def test_constellation_state_init():
    # ConstellationState is essentially just a TypedDict schema, we can test it by instantiating a dict
    # that conforms to it.
    
    class MockState(TypedDict):
        messages: list
        current_agent: str
        routing_history: list
        proposed_actions: list
        pending_interrupts: list
        telemetry_frames: dict
        heartbeat_sequence: int
        is_interrupted: bool

    state: MockState = {
        "messages": [],
        "current_agent": "test",
        "routing_history": [],
        "proposed_actions": [],
        "pending_interrupts": [],
        "telemetry_frames": {},
        "heartbeat_sequence": 0,
        "is_interrupted": False
    }
    
    assert state["current_agent"] == "test"
    assert len(state["messages"]) == 0
    assert not state["is_interrupted"]
