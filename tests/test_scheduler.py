import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from singularity.scheduler.pulse_scheduler import PulseScheduler
from singularity.neural_core.node_base import NodeStatus, DiagnosticFrame

@pytest.fixture
def scheduler():
    sched = PulseScheduler()
    return sched

@pytest.mark.asyncio
async def test_scheduler_start_stop(scheduler):
    with patch.object(AsyncIOScheduler, 'start') as mock_start, \
         patch.object(AsyncIOScheduler, 'shutdown') as mock_shutdown:
        
        await scheduler.start()
        mock_start.assert_called_once()
        assert scheduler.is_running
        
        await scheduler.stop()
        mock_shutdown.assert_called_once()
        assert not scheduler.is_running

@pytest.mark.asyncio
async def test_broadcast_heartbeat(scheduler):
    # This just ensures broadcast_pulse runs without error
    frames = await scheduler.broadcast_pulse()
    assert isinstance(frames, list)
    assert scheduler.sequence_number == 1
