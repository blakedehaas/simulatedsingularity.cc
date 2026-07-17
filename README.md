# 🛰️ Simulated Singularity — Constellation-Class Multi-Agent C2

A multi-agent Command & Control (C2) environment modeled after satellite constellation
operations. Designed for maximum efficiency, scalability, and minimalism.

## Architecture

The system operates across three synchronized layers:

1. **Ground Control** — Human-in-the-Loop (HITL) interface via Chainlit dashboard
2. **Mission Planning** — 60-second heartbeat scheduler (APScheduler)
3. **Orbital Nodes** — Asynchronous agent runtime (LangGraph state machine)

## Agent Constellation

| Agent | Role | Priority |
|-------|------|----------|
| SecurityAgent | Apex Admin — threat assessment & policy enforcement | 0 (highest) |
| CoreAgent | Operator — task routing & resource allocation | 1 |
| EnvironmentAgent | Infrastructure — system & container health | 2 |
| PromptAgent | Comms Relay — message routing & telemetry hub | 3 |
| MemoryAgent | DB Controller — persistence & semantic search | 4 |
| CodingAgent | Architect — code generation & analysis | 5 |
| AnalyticalAgent | Observer — data analysis & anomaly detection | 6 |
| CreativeAgent | Innovator — creative problem-solving | 7 |

## Tech Stack

- **Orchestration**: LangGraph (state-machine with interrupt hooks)
- **Scheduler**: APScheduler (asyncio, SQLAlchemy job store)
- **Persistence**: SQLite via SQLAlchemy (async with aiosqlite)
- **UI**: Chainlit (real-time WebSocket dashboard)

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the Ground Station
chainlit run src/singularity/ground_control/app.py

# Run tests
pytest tests/ -v
```

## Project Structure

```
src/singularity/
├── core/           # AsyncBaseAgent ABC, models, registry
├── agents/         # 8 concrete agent implementations
├── orchestration/  # LangGraph state graph & interrupt hooks
├── scheduler/      # APScheduler heartbeat module
├── persistence/    # SQLAlchemy ORM & data access
├── telemetry/      # Pub/sub event bus & metric collection
└── ground_control/ # Chainlit C2 dashboard
```
