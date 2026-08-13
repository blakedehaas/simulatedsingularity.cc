"""
test_api_app.py — FastAPI endpoint tests for the Simulated Singularity C2 API.

Uses FastAPI TestClient to validate all REST endpoints
across telemetry, console, economy, media, audio, and VR modules.
"""

import logging
import pytest

logger = logging.getLogger(__name__)


def test_health_endpoint(test_api_client):
    """TRACE-API-001: Test /api/health endpoint returns 200."""
    logger.debug("Testing health endpoint")
    response = test_api_client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_telemetry_endpoint(test_api_client):
    """TRACE-API-002: Test /api/telemetry endpoint returns 200."""
    logger.debug("Testing telemetry endpoint")
    response = test_api_client.get("/api/telemetry")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_console_resolve(test_api_client):
    """TRACE-API-003: Test POST /api/console/resolve endpoint."""
    logger.debug("Testing console resolve endpoint")
    payload = {"decision": "APPROVE", "agent_id": "test", "override_prompt": ""}
    response = test_api_client.post("/api/console/resolve", json=payload)
    assert response.status_code == 200
    assert response.json().get("status") == "State Resumed"


def test_console_dispatch(test_api_client):
    """TRACE-API-004: Test POST /api/console/dispatch endpoint."""
    logger.debug("Testing console dispatch endpoint")
    payload = {"prompt": "test directive", "target": "orchestrator"}
    response = test_api_client.post("/api/console/dispatch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "Dispatched"


def test_economy_state(test_api_client):
    """TRACE-API-005: Test GET /api/economy/state endpoint."""
    logger.debug("Testing economy state endpoint")
    response = test_api_client.get("/api/economy/state")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "epochs" in data
    assert "upgrades" in data
    assert "dps" in data


def test_economy_extract(test_api_client):
    """TRACE-API-006: Test POST /api/economy/extract endpoint."""
    logger.debug("Testing economy extract endpoint")
    response = test_api_client.post("/api/economy/extract")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"] > 0


def test_economy_upgrade_insufficient_funds(test_api_client):
    """TRACE-API-007: Test POST /api/economy/upgrade fails without enough data."""
    logger.debug("Testing economy upgrade with insufficient data")
    payload = {"upgrade_id": "keystroke"}
    response = test_api_client.post("/api/economy/upgrade", json=payload)
    # Should fail since we start with ~1 data and keystroke costs 10
    assert response.status_code == 400


def test_media_generate_video(test_api_client):
    """TRACE-API-008: Test POST /api/media/generate/video endpoint."""
    logger.debug("Testing media generate video endpoint")
    payload = {"prompt": "Generate a satellite flyby render"}
    response = test_api_client.post("/api/media/generate/video", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "processing"


def test_audio_tts(test_api_client):
    """TRACE-API-009: Test POST /api/audio/tts/agent endpoint."""
    logger.debug("Testing audio tts endpoint")
    payload = {"agent_id": "orchestrator", "text_payload": "Matrix sync complete."}
    response = test_api_client.post("/api/audio/tts/agent", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["profile"] == "deep_resonance_v1"


def test_vr_state(test_api_client):
    """TRACE-API-010: Test GET /api/vr/state endpoint."""
    logger.debug("Testing vr state endpoint")
    response = test_api_client.get("/api/vr/state")
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
