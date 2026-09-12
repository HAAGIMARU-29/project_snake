# Testing and performance

[Documentation index](README.md)

## Run the suite

From the project directory:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

Use targeted tests while developing, then the full suite before accepting a behavior change:

```bash
.venv/bin/python -m pytest tests/test_phase4_food.py -q
.venv/bin/python -m pytest tests/test_phase8_royale.py tests/test_phase10_search.py -q
.venv/bin/python -m pytest -q
```

The checked-in [validation output](../reports/pytest.txt) records 205 passing tests under Python 3.13.15. Four deprecation warnings come from Flask 2.3.2's use of Python APIs, rather than failing bot assertions. Treat this as a recorded result for the documented implementation, not a substitute for running tests after a change.

## Test organization

| File | Main coverage |
|---|---|
| [`test_phase1_safety.py`](../tests/test_phase1_safety.py) | Directions, bounds, walls, bodies, deterministic responses, fallback |
| [`test_phase2_space.py`](../tests/test_phase2_space.py) | Flood fill, partitions, exits, trap penalties, optional evaluation calls |
| [`test_phase3_heads.py`](../tests/test_phase3_heads.py) | Enemy lengths, contested cells, maximum threat, field shape, mutation |
| [`test_phase4_food.py`](../tests/test_phase4_food.py) | Health bands, BFS detours, food contests, unreachable food, food traps |
| [`test_phase5_tail.py`](../tests/test_phase5_tail.py) | Own tail release, growth/stacking, conservative enemy tails, escape, no mutation |
| [`test_phase6_standard_strategy.py`](../tests/test_phase6_standard_strategy.py) | Player-count profiles and safety separation |
| [`test_phase7_territory.py`](../tests/test_phase7_territory.py) | Symmetry, ties, body walls, disconnected regions, normalization |
| [`test_phase8_royale.py`](../tests/test_phase8_royale.py) | Hazard health, food reset, safe routes, escape, 19×19 support |
| [`test_phase9_aggression.py`](../tests/test_phase9_aggression.py) | Shorter-enemy pressure, gates, exit/food denial, population scaling |
| [`test_phase10_search.py`](../tests/test_phase10_search.py) | Simulation, head collisions, legal result, deadline fallback, determinism |
| [`test_integration.py`](../tests/test_integration.py) | Complete `move()` behavior over 16 named scenarios |
| [`test_invariants.py`](../tests/test_invariants.py) | 40 fixed random seeds; valid outputs, bounded helpers, no mutation |
| [`test_performance.py`](../tests/test_performance.py) | Repeated timings and pathological larger boards |
| [`test_baseline_regressions.py`](../tests/test_baseline_regressions.py) | All walls/exits and equivalence of optional precomputed calls |
| [`test_hardening.py`](../tests/test_hardening.py) | Logging, death categories, Flask routes, tail head-risk, energy starvation, real tactical regression |

The original Phase 1–3 files were preserved through implementation. Some early tests use deliberately artificial blockers; not every fixture is a physically reachable game history. The integration and randomized tests complement those isolated helper cases.

## Fixture helpers

[`tests/fixtures.py`](../tests/fixtures.py) supplies:

- `make_snake(snake_id='you', body=None, health=100, name=None)`.
- `make_state(width=11, height=11, you=None, enemies=None, food=None, hazards=None, turn=0, ruleset='standard')`.
- `body_at(points)` to turn coordinate tuples into API dictionaries.
- `integration_scenarios()` for the shared named board collection.

The default snake has three segments with its head at `(5, 5)`. `make_state` includes our snake in `board.snakes`. Fixture objects can share references between `you` and the board entry; use `copy.deepcopy` when retaining a before-state for mutation checks or deriving independent scenarios.

The 16 integration scenarios cover open Standard, four snakes, food emergency, equal heads, own-tail escape, uncertain enemy tails, territory split, duel, Royale 11×11/19×19, fully trapped, no food, many foods, many hazards, long bodies, and simultaneous threats.

A saved [`tactical_regression.json`](../tests/tactical_regression.json) captures a state where the heuristic prefers `up` but search finds a less dangerous `down` route. Keep the real board when a future failure becomes a regression; it is stronger evidence than asserting an implementation-specific arithmetic identity.

## Invariants

Fixed-seed tests exercise 7×7, 11×11, and 19×19 boards with up to four snakes. They check valid directions, deterministic repeated calls, input preservation, valid field keys, bounded flood-fill counts, and exit counts in 0–4.

Randomness is confined to fixture generation with a local seeded generator. The bot itself has no random move selection. These tests sample plausible boards; they are not an exhaustive proof of correctness for all game states.

## Flask route testing

The route regression constructs the actual Flask app with `app.run` disabled, then sends requests with Werkzeug's WSGI client. This exercises the routing and response header without opening a network socket.

Flask 2.3.2's convenience `app.test_client()` expects a Werkzeug version attribute absent from the installed Werkzeug version. The test uses Werkzeug's supported client instead. Real CLI matches separately validate the HTTP server path.

## Performance assertions

```bash
.venv/bin/python -m pytest tests/test_performance.py -q -s
```

The main parameterized test performs eight calls for seven scenarios with search both enabled and disabled. It checks:

- Every call remains below `HARD_CUTOFF_SECONDS + 0.08`, currently 350 ms, to allow scheduling overhead.
- Without search, each scenario's average remains below 50 ms.
- Every result contains a valid direction.

An additional test covers a 19×19 board dense with both food and hazards, and a 19×19 board with nearby enemies. The 350 ms assertion is a generous regression threshold, not the operational target or proof of a strict 270 ms wall-clock maximum.

## Reproducible benchmark

```bash
.venv/bin/python scripts/benchmark.py
```

The script warms each configuration once, runs 30 measured calls, and reports mean, P95, and maximum using `perf_counter`. P95 uses the sorted sample at `ceil(0.95 × n) - 1`. It covers seven scenarios with search enabled and disabled: 420 measured calls total.

Output is printed as JSON and written to [`reports/benchmark.json`](../reports/benchmark.json), replacing its previous contents. The Python version is included; hardware and deployment environment are not automatically recorded. Standard output is redirected during calls, so terminal rendering is excluded, but enabled telemetry formatting and buffer writes are still part of the measured call.

The benchmark is a developer tool and imports the test fixtures. Run it from a development checkout containing `tests/`.

## Recorded results

Search-enabled synthetic measurements from the existing benchmark artifact:

| Scenario | Mean ms | P95 ms | Maximum ms |
|---|---:|---:|---:|
| Four-snake Standard | 5.352 | 5.881 | 6.067 |
| Partitioned Standard | 3.148 | 4.485 | 4.580 |
| Royale 11×11 | 8.842 | 14.328 | 15.371 |
| Royale 19×19 | 24.471 | 27.781 | 27.894 |
| Long snake | 1.091 | 1.712 | 2.524 |
| Many food cells | 6.557 | 7.841 | 9.606 |
| Many hazard cells | 4.704 | 6.019 | 6.033 |

Final baseline games recorded 1,150 bot decisions: mean 17.14 ms, P95 37.46 ms, maximum 48.91 ms. Final self-play recorded 5,005 decisions across all four copies: mean 28.81 ms, P95 79.45 ms, maximum 204.73 ms. Both final batches had zero search deadline fallbacks; the final self-play log review found zero HTTP/timeout errors.

These are different workloads, so their distributions should not be merged into a single claimed benchmark. The full development record contains 39 CLI matches. See [match metrics](../reports/match_metrics.json) and [Operations](operations.md) to reproduce match-based validation.
