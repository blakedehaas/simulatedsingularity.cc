import pytest
import asyncio
from unittest.mock import patch, MagicMock

from singularity.sensorium.events import SensoriumEventBus, SensoriumEvent, SensoriumEventType
from singularity.sensorium.collector import SensoriumCollector
from singularity.neural_core.node_base import DiagnosticFrame, NodeStatus

@pytest.fixture
def event_bus():
    return SensoriumEventBus()

@pytest.fixture
def collector(event_bus):
    c = SensoriumCollector(bus=event_bus)
    c.start()
    return c

@pytest.mark.asyncio
async def test_event_bus_publish(event_bus):
    received = []
    async def handler(event):
        received.append(event)
    
    event_bus.subscribe(SensoriumEventType.HEARTBEAT, handler)
    event = SensoriumEvent(
        event_type=SensoriumEventType.HEARTBEAT,
        source_node_id="test",
        data={"test": "data"}
    )
    await event_bus.publish(event)
    
    assert len(received) == 1
    assert received[0].data["test"] == "data"

@pytest.mark.asyncio
async def test_collector_record(collector, event_bus):
    frame = DiagnosticFrame(
        node_id="test-agent",
        status=NodeStatus.NOMINAL,
        metrics={"cpu": 10.0},
        message="Test message"
    )
    
    event = SensoriumEvent(
        event_type=SensoriumEventType.NODE_RESPONSE,
        source_node_id="test-agent",
        data={"telemetry": frame.model_dump()}
    )
    await event_bus.publish(event)
    
    # Allow event loop to process the queue
    await asyncio.sleep(0)
    
    latest_frame = collector.get_latest_frame("test-agent")
    assert latest_frame is not None
    assert latest_frame.node_id == "test-agent"
