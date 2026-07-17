# Simulated Singularity CC

The Constellation-Class Command & Control (C2) environment. Modeled after satellite constellation operations, this system utilizes a Python-centric stack to implement an asynchronous multi-agent orchestrator driven by LangGraph, Chainlit, and an extensible agent framework.

## Project Structure
- `src/singularity/ground_control/`: Human-in-the-loop Chainlit HTML-5 dashboard.
- `src/singularity/orchestration/`: LangGraph state-machine orchestrator enforcing priority-based routing and manual interrupt breakpoints.
- `src/singularity/agents/`: Constellation orbital nodes subclassing `AsyncBaseAgent`.
- `tests/`: Exhaustive `pytest` testing infrastructure asserting exact 100% test coverage.

## Setup and Installation

1. Activate your virtual environment:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. Install the project in editable mode so the `singularity` CLI is mapped:
   ```powershell
   uv pip install -e .
   ```

## Using the CLI

The `singularity` CLI is the main entry point to the system. It exposes several flags for interaction, testing, and operations.

| Flag | Description |
| ---- | ----------- |
| `-h, --help` | **Interactive Documentation:** Generates and launches a highly detailed, interactive HTML dashboard containing code snippets, architectural breakdowns, and a simulated context-aware LLM chatbot assistant. |
| `-v, --verbose` | **Verbose Mode:** Overrides logging layers to `DEBUG` and traces the entire LangGraph execution pipeline, printing telemetry metrics directly to the terminal. |
| `-t, --test` | **Test Suite Trigger:** Automatically triggers the integrated `pytest` testing environment and calculates coverage. If coverage drops below 100%, it simulates delegating the refactoring task to autonomous coding subagents. |
| `-i, --interactive` | **Ground Control:** Initiates the `chainlit` server subprocess, opening the human-in-the-loop Ground Control dashboard for direct manual interaction with the agent constellation. |
| `-a, --autonomous` | **Headless Loop:** Bypasses manual interrupt checkpoints and continuously runs the LangGraph orchestration layer in an infinite loop, processing periodic heartbeats. |
| `-s, --sandbox` | **Sandbox Mode:** Restricts the environment heavily and forces the sqlite database to execute entirely in-memory using `:memory:` mapping. Prevents any persistent state alterations. |

## Testing

This project enforces a rigorous 100% line coverage standard across its core modules (`agent_base`, `models`, `persistence`, `agents`). Testing is instrumented via `pytest`, `pytest-cov`, and `pytest-asyncio`, with massive reliance on `unittest.mock` for isolating dependencies like LLM inference.

**To run the test suite:**
```powershell
singularity --test
```

Alternatively, you can invoke `pytest` directly:
```powershell
pytest tests/ --cov=src/singularity --cov-report=term-missing
```

### Coverage Automation
If you introduce a feature that isn't fully tested, the `singularity --test` command will detect the dip in code coverage via stdout capture and autonomously spin up coding subagents to rebuild the tests until the strict 100% target is achieved once again.

## In-Depth Help
To dive deeper into the technical interfaces, such as implementing `AsyncBaseAgent` or understanding the `LangGraph` interrupt loops, invoke the generated interactive documentation:
```powershell
singularity --help
```
You can use the simulated **Architect LLM** chat window within the generated HTML page to query structural decisions!
