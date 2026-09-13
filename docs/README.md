# SEDS Hackathon Battlesnake documentation

This project extends the official Python Battlesnake starter into a deterministic bot for Standard multiplayer and Royale. It combines physical collision checks, reachable space, health-aware food routing, conservative tails, territory, controlled pressure, and bounded tactical search. The main tournament board sizes are 11×11 and 19×19.

These guides describe the checked-in implementation. Historical measurements are identified as recorded results; they are not promises about a different machine or deployment.

## Reading guide

| Guide | What it covers |
|---|---|
| [Getting started](getting-started.md) | Environment, installation, local server, CLI games, Docker, and configuration |
| [Deployment](deployment.md) | Container launch, public URL requirements, hackathon checklist, and failure checks |
| [Architecture](architecture.md) | Repository layout, request lifecycle, representations, dependencies, and invariants |
| [HTTP API and game state](api-and-state.md) | Routes, request fields, coordinate conventions, example payload, and input assumptions |
| [Strategy and scoring](strategy-and-scoring.md) | Every score component, constants, food, tails, Standard profiles, territory, and Royale |
| [Tactical search](search.md) | Simulation, plausible responses, pruning, deadlines, fallback, and approximation limits |
| [Minimax plan](minimax-plan.md) | Staged Alpha-Beta/MaxN design, APIs, gates, risks, and implementation checkpoints |
| [Python function reference](function-reference.md) | Helper contracts, arguments, returns, compatibility, and usage examples |
| [Testing and performance](testing-and-performance.md) | Test organization, fixtures, invariants, benchmarks, and recorded results |
| [Tournament operations](operations.md) | Practice runner, ports, artifacts, telemetry, death analysis, and troubleshooting |
| [Development and tuning](development.md) | Change workflow, regression requirements, tuning, limitations, and implementation history |

For a first run, start with Getting started, then Tournament operations. To work on the bot, read Architecture, Strategy and scoring, and the function reference. To diagnose a loss, use the scoring inspection example and compare it with the replay and engine death cause.

## Project at a glance

- Runtime: Python and Flask; the recorded validation used Python 3.13.15 and Flask 2.3.2.
- Local server: `http://localhost:8000`, configurable through `PORT`.
- Entry point: [`main.py`](../main.py); HTTP routing: [`server.py`](../server.py).
- Tactical search: [`snake/search.py`](../snake/search.py).
- Development dependency: pytest, listed in [`requirements-dev.txt`](../requirements-dev.txt).
- Decision targets: normal compute below 50 ms, P95 below 100 ms, cooperative internal cutoff of 270 ms.
- Recorded validation: 205 passing tests and 39 real CLI games across development and final validation.

## Documentation versus evidence

The guides explain how the project works. The existing [`reports/`](../reports/) directory retains implementation checkpoints and measured evidence:

- [Phase report](../reports/PHASE_REPORT.md): phase-by-phase changes and test counts.
- [Tournament report](../reports/TOURNAMENT_REPORT.md): implementation handoff, constants, and results.
- [Recorded pytest output](../reports/pytest.txt).
- [Synthetic benchmark data](../reports/benchmark.json).
- [Match metrics](../reports/match_metrics.json).
- [Final baseline matches](../reports/final-baseline/summary.json) and [final self-play matches](../reports/final-selfplay/summary.json).

All shell examples assume a terminal in `starter-snake-python/` unless a command explicitly changes directory. Links are relative so the documentation can be read in a clone or repository browser.
