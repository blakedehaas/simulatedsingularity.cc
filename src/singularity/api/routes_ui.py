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
                "grid": { "x": 0, "y": 0, "w": 3, "h": 25 },
                "elements": [
                    {
                        "type": "custom",
                        "component": "SimulationConfigWidget"
                    }
                ]
            },
            {
                "id": "diagnostics",
                "title": "System Diagnostics",
                "colorClass": "text-yellow-400",
                "grid": { "x": 3, "y": 0, "w": 3, "h": 25 },
                "elements": [
                    { "type": "text", "style": "header", "value": "MATRIX STATUS" },
                    { "type": "gumball", "color": "green", "label": "Orchestrator Node" },
                    { "type": "gumball", "color": "green", "label": "Execution Node" },
                    { "type": "gumball", "color": "cyan", "label": "Safeguard Node" },
                    { "type": "switch", "id": "override_mode", "label": "Manual Override" },
                    { "type": "text", "style": "paragraph", "value": "System throughput metrics:" },
                    { 
                        "type": "bar_graph", 
                        "label": "CPU Load (%)", 
                        "max": 100, 
                        "data": [
                            { "label": "Core 0", "value": 12 },
                            { "label": "Core 1", "value": 89 },
                            { "label": "Core 2", "value": 45 }
                        ]
                    },
                    { 
                        "type": "table", 
                        "columns": ["Agent", "Status", "Latency"], 
                        "rows": [
                            ["Orch", "OK", "12ms"],
                            ["Exec", "OK", "45ms"],
                            ["Safe", "WARN", "120ms"]
                        ]
                    },
                    { "type": "text", "style": "header", "value": "INTERVENTION" },
                    { "type": "textbox", "id": "diag_command", "label": "Override Command", "placeholder": "Enter system command..." },
                    { "type": "button", "label": "Execute", "action": { "method": "POST", "url": "/api/health", "payloadFrom": ["override_mode", "diag_command"] } }
                ]
            },
            {
                "id": "visualizer",
                "title": "Swarm Topology Visualizer",
                "colorClass": "text-purple-400",
                "grid": { "x": 6, "y": 0, "w": 6, "h": 12 },
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
                "grid": { "x": 6, "y": 12, "w": 6, "h": 13 },
                "elements": [
                    {
                        "type": "custom",
                        "component": "C2Terminal"
                    }
                ]
            }
        ]
    }
