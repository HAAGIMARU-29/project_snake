# Tournament operations and troubleshooting

[Documentation index](README.md)

## Before practice

Run from `starter-snake-python/`. Verify the selected interpreter and CLI, then run the suite:

```bash
.venv/bin/python --version
battlesnake play --help
.venv/bin/python -m pytest -q
```

For manually managed games, start `main.py` and check `GET /` as described in [Getting started](getting-started.md). Restart a running process after modifying the bot; an already-running server does not automatically load edits.

## Repeated practice runner

[`scripts/practice.py`](../scripts/practice.py) launches temporary Flask servers on ports **8100** and **8101**. It does not use or restart a manually managed server on port 8000.

Use a distinct output directory for a new batch:

```bash
.venv/bin/python scripts/practice.py --output reports/practice-session-1
.venv/bin/python scripts/practice.py --self-play \
  --seeds 404 505 606 --output reports/selfplay-session-1
```

| Argument | Default | Meaning |
|---|---|---|
| `--output PATH` | `reports/practice` | Artifact directory, resolved from the command's current directory |
| `--seeds N [N ...]` | `101 202 303` | Integer CLI seeds |
| `--self-play` | Off | Use the current bot as opponent instead of the preserved baseline |

For every seed, the runner plays four-snake Standard 11×11, Royale 11×11, and Royale 19×19. Three seeds produce nine games. The designated bot uses port 8100; three opponents share port 8101. The CLI gets a 500 ms request timeout and each match subprocess has a 120-second overall limit.

Without `--self-play`, opponents run the preserved Phase 3 code from Git commit `25b0cd6`. The script retrieves that file with `git show` into a temporary directory. The current script also retrieves this baseline before starting a self-play batch, so that commit must exist in local history in either mode.

The runner inherits the environment, including `BATTLESNAKE_SEARCH`. It overrides each server's `PORT`, `PYTHONPATH`, `PYTHONUNBUFFERED`, and `BATTLESNAKE_LOG=1` so decision logs are captured. Use the project interpreter to ensure the subprocess servers have Flask installed.

Ports are checked before startup, including socket reuse for recently closed connections. An existing listener causes the run to stop. The runner terminates only the processes it created in its cleanup block. It writes a summary of completed matches even when a later match fails within that block.

## Artifacts and repeatability

| Output | Contents |
|---|---|
| `bot.log` | Current bot startup and telemetry |
| `opponent.log` | Opponent server output; interleaved snake requests in self-play |
| `<mode>-<size>-<seed>.log` | CLI output, including board views and explicit elimination causes |
| `<mode>-<size>-<seed>.jsonl` | Engine replay: initial game metadata, successive game-state frames, final result |
| `summary.json` | Opponent identifier, match settings, duration, winner, and engine death causes |

Files with the same names are overwritten when the same output directory is reused. Choose a new path to preserve an earlier run. Detailed `.log` and `.jsonl` files one directory below `reports/` are gitignored; summaries and aggregate JSON files can be committed. Gitignored replays may not exist in a fresh clone even when the checked-in summary does.

A seed is useful for repeating an experiment, but the CLI also generates snake IDs and schedules requests. Save the full replay, code revision, environment, and summary when comparing changes. The same seed alone is not a guarantee of the same complete match history.

## Decision telemetry

Per-move logs are compact JSON lines. Fields are:

| Field | Interpretation |
|---|---|
| `event` | `move` |
| `turn`, `game_id`, `snake_id` | Join keys for a particular request |
| `decision_time_ms` | Compute elapsed to just before log serialization/output |
| `chosen_move` | Returned direction |
| `scores` | Chosen candidate's component values, rounded to two decimals |
| `snakes_alive`, `health`, `ruleset` | Context for tuning |
| `search_timeout` | Search exhausted its cooperative deadline |
| `fallback` | No hard-safe direction existed; the deterministic `down` response was used |

The log contains only the chosen candidate's components. To compare alternatives, replay the pre-move state through `score_move_components`, using the [inspection example](function-reference.md).

Timing does not include network transit or the completed log write. Captured server files also contain non-JSON startup and lifecycle lines; parse JSON only where appropriate. Disable just the per-move log with `BATTLESNAKE_LOG=0` for an independently started server.

`end` emits `event: end`, identifiers, `outcome`, and `death_reason`. `outcome: survived` means our ID remains in the final board list; it is not a calculated ranking.

## Investigating a death

1. Read `summary.json` for the engine's cause and elimination turn.
2. Locate the frame immediately before that turn and the matching snake ID. Replay frames do not necessarily have a `you` field; set it to the snake being inspected.
3. Check which moves were hard-safe with `tail_aware=True`.
4. Inspect all heuristic components and the actual chosen decision log.
5. Determine whether search found a bad response, ran out of time, or had no safer alternative.
6. Look several turns earlier if the final move was already forced.

| Cause / category | First investigation |
|---|---|
| WALL | Was the snake already trapped and using the no-safe-move fallback? |
| BODY | Was a middle segment entered, or did earlier choices close an escape? |
| HEAD_TO_HEAD | Compare lengths, possible enemy responses, and unique-tail threats |
| STARVATION | Check health bands, route existence, food contests, and Royale energy cost |
| HAZARD | Check remaining health, food reset, affordable safe access, and newly added hazards |
| TRAPPED | Check space, exits, tail conservatism, and preceding bottleneck entry |
| TIMEOUT | Compare compute logs with engine HTTP errors and external latency |
| UNKNOWN | End payload lacks enough evidence; use the engine replay/log |

A wall or body death does not by itself prove a hard-safety bug: the bot must still return a direction when every move loses. Likewise, `search_timeout: true` is not an engine timeout; it is an intentional fallback mechanism.

## Troubleshooting

| Symptom | Action |
|---|---|
| `No module named pytest` or `flask` | Install the appropriate requirements with the same `.venv/bin/python` used to run the command |
| Wrong Python version | Use the explicit project interpreter rather than a different activated environment |
| Port 8000 already in use | Check which process owns it; use another `PORT` for an independent server or deliberately restart the existing bot |
| Practice ports 8100/8101 occupied | Stop the conflicting manually managed service or change the runner's port assignments consistently; there is no port CLI option |
| `battlesnake: command not found` | Make the installed CLI executable available on `PATH` |
| Baseline Git revision missing | Restore/fetch the repository history containing `25b0cd6`; the current runner needs it even for self-play |
| Server startup fails | Inspect the corresponding `bot.log` or `opponent.log`; check dependencies and permissions to open local sockets |
| `/move` raises an exception | Confirm JSON content type, a nonempty `you.body`, consistent snake IDs, and required board dimensions/list |
| Editing code seems ineffective | Restart the server process used by the game's URL |
| `app.test_client()` hits Werkzeug metadata error | The route regression uses Werkzeug's WSGI client; see [Testing](testing-and-performance.md) |
| Docker build unexpectedly large | The existing Dockerfile copies the full context and there is no `.dockerignore`; see [Getting started](getting-started.md) |
| High move latency | Compare heuristic-only versus search timing, inspect dense food/nearby enemy cases, then measure hosting and network overhead separately |

## Tournament handoff

Keep the exact revision and parameters used for each practice batch. Verify the URL from the actual engine environment, confirm Standard and Royale on the intended board sizes, and retain a known passing revision for comparison. During the final hardening window, favor regression fixes and one-parameter experiments over adding a new search architecture.
