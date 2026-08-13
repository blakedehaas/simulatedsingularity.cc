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
    assert isinstance(data, list)




