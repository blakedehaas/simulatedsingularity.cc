from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ui", tags=["UI"])

@router.get("/schema")
async def get_ui_schema():
    """Returns the JSON schema defining the dynamic SDUI panels and their API hooks."""
    return {
        "version": "1.0",
        "panels": [
            {
                "id": "config",
                "title": "Simulation Configuration",
                "colorClass": "text-emerald-400",
                "grid": { "x": 0, "y": 0, "w": 4, "h": 25 },
                "elements": [
                    {
                        "type": "custom",
                        "component": "SimulationConfigWidget"
                    }
                ]
            },
            {
                "id": "visualizer",
                "title": "Swarm Topology Visualizer",
                "colorClass": "text-purple-400",
                "grid": { "x": 4, "y": 0, "w": 8, "h": 12 },
                "elements": [
                    {
                        "type": "custom",
                        "component": "ProductionSwarmVisualizer"
                    }
                ]
            },
            {
                "id": "terminal",
                "title": "Global Observation Deck",
                "colorClass": "text-cyan-400",
                "grid": { "x": 4, "y": 12, "w": 8, "h": 13 },
                "elements": [
                    {
                        "type": "custom",
                        "component": "C2Terminal"
                    }
                ]
            }
        ]
    }
