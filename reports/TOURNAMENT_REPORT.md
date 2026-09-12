# Tournament bot implementation

The starter was extended in place through isolated phase commits. All original tests are preserved. `server.py`, appearance, port configuration, and HTTP contracts remain compatible.

## Architecture

- `main.py`: existing handlers and safety/flood-fill API, food BFS, tail occupancy, strategy profiles, territory, Royale energy costs, pressure, component scores, and decision telemetry.
- `snake/search.py`: simultaneous-turn simulator and bounded worst-response tactical search.
- `tests/`: original Phase 1–3 tests, Phase 4–10 tests, integration scenarios, fixed-seed invariants, performance, and hardening checks.
- `scripts/benchmark.py`: 30 repeated calls per configuration, reporting mean/P95/max.
- `scripts/practice.py`: repeated real CLI games against the preserved Phase 3 baseline or self-play, with temporary servers on 8100/8101, replay capture, and engine death-cause summaries. It stops only the processes it starts.

No mutable global match state, database, ML, NumPy, or new runtime dependency. `requirements-dev.txt` contains pytest. Global tables are configuration only and are never mutated during matches.

## Scoring and constants

`evaluate_move` returns the sum of `score_move_components`. Live search adds a tactical penalty to each candidate and chooses the highest resulting score. Ties follow `up`, `right`, `down`, `left`. No-safe-move fallback remains `down`.

| Component / control | Value and meaning |
|---|---|
| Physical safety | Wall or non-vacating body = negative infinity; excluded from move candidates |
| `SPACE_WEIGHT` | 1.0 × reachable cells, capped at 400 cells to bound rewards |
| `EXIT_WEIGHT` | 3.0 per hard-safe exit |
| `TRAP_PENALTY` | 1,000 when reachable region is shorter than post-eating length; 500 for a space/length ratio below 1.5 |
| `SPACE_RATIO_THRESHOLD` | 1.5 |
| `BASE_CELL_WEIGHT` | 0.0 |
| `HEAD_DANGER_PENALTY` | 10,000 for a possible equal/larger enemy head arrival; maximum enemy length wins |
| `SHORTER_ENEMY_HEAD_BONUS` | 0.0 in the base field; controlled bonuses live in aggression |
| Food urgency | Health >70: 4; 41–70: 30; 21–40: 90; ≤20: 240 |
| Food attraction | Best food's urgency × region quality × contest factor / (BFS distance from candidate + 1); max, not sum |
| Food contest / dead-end discount | 0.1 each; equal/larger enemy arriving no later discounts food; losing immediate head cells are excluded from food routes |
| `FOOD_TARGET_LIMIT` | 12 reachable targets, ranked deterministically by BFS distance from our head |
| Starvation | 1,500 penalty at health ≤20 with no food reachable in time; 10,000 for immediate health death |
| Territory | Owned cells / free cells; equal arrivals contested; no length tie bonus |
| Hazard damage | `hazardDamagePerTurn` setting, default 14 |
| Hazard entry cost | −min(400, damage × (1 + 50 / remaining health)); lethal entry −10,000 |
| Hazard food | Health resets to 100; no damage on that food cell |
| Future safe access | Up to +25 × affordable non-hazard cells / board area; −1,500 if neither safe space nor food is affordable |
| Aggression | Best shorter target only; 60 × normalized space reduction + 8 per denied exit + 12 head pressure + 8 restricted-escape bonus + 12 food denial; capped at 80 before profile scaling |
| Aggression gates | Health >40, ample own space for length+1, no equal/larger head risk, no costly hazard entry |
| `SEARCH_DEATH_PENALTY` | 20,000 for a modeled fatal response or no safe next exit; 1,000 for insufficient next-step space |
| `RELEVANT_ENEMY_DISTANCE` | 4 grid steps: enumerate all plausible responses within two-turn tactical reach; use one representative move for distant enemies |
| `SEARCH_BUDGET_SECONDS` | 0.22 |
| `HARD_CUTOFF_SECONDS` | 0.27 for the whole decision, further reduced to 60% of the request timeout |

Positive rewards remain far below immediate-fatal penalties. Territorial and aggressive rewards are suppressed in traps. Head danger stays a large soft penalty, allowing a valid response even when all directions are bad. Hard occupancy is never encoded as a strategic weight. Flood-fill survival never reads strategic weights.

| Snakes alive | Space multiplier | Food multiplier | Territory weight | Aggression multiplier | Head-pressure weight |
|---|---:|---:|---:|---:|---:|
| 4+ | 1.2 | 0.8 | 15 | 0.15 | 1.8 |
| 3 | 1.1 | 0.9 | 30 | 0.45 | 5.4 |
| 2 | 1.0 | 1.0 | 60 | 1.0 | 12 |
| 1 | 1.0 | 1.0 | 0 | 0 | 0 |

Hazard multiplier is 1.0 in all profiles. `head_pressure_weight` exposes the derived head-pressure coefficient; aggression scales its 12-point term by the same multiplier.

## Standard and Royale behavior

Standard prioritizes physical safety and reachable space, avoids equal/larger head contests, follows reachable food as health falls, and releases a unique own tail on non-eating moves. Four-player games are conservative; duels put more weight on territory and pressure against shorter snakes. Enemy tails remain blocked for our choices, while threat modeling pessimistically considers tails that could vacate.

Royale keeps hazards traversable. Immediate health and cumulative path damage influence food and future safe access. A survivable hazard escape can beat a trapped safe cell. The bot rewards access to non-hazard space rather than geometric center. The same computations use board dimensions on 11×11 and 19×19.

Search models simultaneous motion, health, food, growth, bodies, and length-based head collisions, then checks the best safe next exit under the worst enemy response. It is not deep minimax. Work is bounded, deadlines are checked cooperatively, and an incomplete search is discarded in favor of the heuristic fallback. OS scheduling and an individual bounded operation can add slight deadline overhead; this is not a hard-realtime guarantee.

## Validation

205 tests pass under Python 3.13.15 / Flask 2.3.2. Four deprecation warnings originate in Flask's use of Python APIs slated for removal in Python 3.14. No earlier test was rewritten. Full details and per-phase counts are in `PHASE_REPORT.md`.

A live-practice review found four starvation deaths in six self-play games. Royale starvation checks now use cumulative hazard energy, and the exit bonus was reduced from 5 to 3 to reduce detours away from food. No major algorithm was added during hardening.

Benchmark measurements and match summaries are recorded alongside this report. Synthetic benchmarks cover 420 timed decisions (30 repetitions × seven scenarios × two search settings). See `benchmark.json` for the exact measurements and interpreter version.

## Measured performance

Final synthetic benchmark, milliseconds (30 calls per row; search enabled):

| Scenario | Mean | P95 | Maximum |
|---|---:|---:|---:|
| Four-snake Standard 11×11 | 5.35 | 5.88 | 6.07 |
| Partitioned Standard | 3.15 | 4.49 | 4.58 |
| Royale 11×11 | 8.84 | 14.33 | 15.37 |
| Royale 19×19 | 24.47 | 27.78 | 27.89 |
| Long snake | 1.09 | 1.71 | 2.52 |
| Many food cells | 6.56 | 7.84 | 9.61 |
| Many hazard cells | 4.70 | 6.02 | 6.03 |

Without search, all scenario averages were below 24 ms. The maximum observed heuristic call was 28.99 ms. Separate tests cover an extreme food/hazard-dense 19×19 board, nearby enemies, and already-expired/mid-search deadlines. Timing is local compute, not network transit or hosted-server scheduling.

The tuned bot won all nine final baseline games (three each of Standard 11×11, Royale 11×11, Royale 19×19) against three copies of commit `25b0cd6`. Its 1,150 measured decisions averaged 17.14 ms, P95 37.46 ms, maximum 48.91 ms, with zero search deadline fallbacks. Self-play measurements and engine death categories are in `match_metrics.json` and the individual batch `summary.json` files. Full local replays and logs are gitignored to avoid committing large generated files.

Initial self-play used nine games; six additional games supplied exact engine death causes. Those six games produced 6 hazard deaths, 4 starvation deaths, 5 body/self collisions, 2 head collisions, and 1 wall collision. This prompted the hazard-aware starvation fix and exit-weight reduction. A further final self-play batch checks the tuned version. The small sample does not establish that tuning improves tournament win rate; self-play is primarily a failure and latency diagnostic. CLI-generated snake IDs and simultaneous request scheduling also mean a seed alone is not a complete replay identity. The bot itself is deterministic on a fixed request.

## Run and tune

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python main.py
.venv/bin/python scripts/benchmark.py
.venv/bin/python scripts/practice.py
.venv/bin/python scripts/practice.py --self-play --output reports/new-practice
```

Set `BATTLESNAKE_SEARCH=0` to reproduce heuristic-only play. Set `BATTLESNAKE_LOG=0` to silence per-move telemetry. The default is search and compact logs enabled. Logs identify game and snake, chosen move, timing, component scores, player count, health, ruleset, and deadline fallback. Death categories are WALL, BODY, HEAD_TO_HEAD, STARVATION, TRAPPED, HAZARD, TIMEOUT, and UNKNOWN when evidence is absent.

Tune during practice, changing one parameter at a time:

1. Food urgency at health 40–70 if starvation or persistent length deficits dominate. Watch whether food changes increase head collisions.
2. `SPACE_RATIO_THRESHOLD` and trap penalties if self-enclosure dominates. Static space may underestimate escape via future tails.
3. Hazard sensitivity (50 / remaining health), safe-access weight 25, and food discounts if hazards cause avoidable deaths.
4. Duel aggression and territory weights only after survival metrics remain stable.
5. Reduce the search budget or food-target limit if deployment latency differs materially from local measurements. Keep the 10,000/20,000 fatal penalties separated from bounded rewards.

## Remaining weaknesses

- Static BFS does not model body motion beyond the immediate own tail; conservative enemy-tail occupancy can reject a real escape.
- Food paths exclude current head-danger cells even for later arrival, and only the first 12 reachable targets are evaluated. Energy routing does not plan chains of health resets.
- Space size is a proxy for survival; it does not prove a long self-avoiding path. Voronoi ignores future body movement and does not prove a kill.
- Search approximates only a short horizon, uses representative distant-enemy moves, and does not spawn food or predict random shrink direction.
- Equal-length mutual deaths, encirclement, and future hazard shrink can still defeat the bot. A baseline win rate is not evidence of strength against the other hackathon teams.
- `/end` can omit elimination metadata. Unknown causes are left unknown; the practice runner's engine log supplies explicit causes for tuning.

## Rules reference

Hazard-food handling and simultaneous simulation were checked against the [official Standard rules implementation](https://github.com/BattlesnakeOfficial/rules/blob/main/standard.go) and the installed CLI rules v1.2.3. The food hazard exception and pop-tail/grow order are covered by tests.

## Final live validation

The final six self-play matches completed successfully, with the designated copy winning 3/6. Across 5,005 decisions from all four identical copies, mean compute was 28.81 ms, P95 79.45 ms, and maximum 204.73 ms. There were 0 search-deadline fallbacks and 0 observed HTTP/timeout errors. Engine death causes: {'head-collision': 2, 'snake-self-collision': 2, 'wall-collision': 1, 'snake-collision': 2, 'hazard': 8, 'out-of-health': 3}. Starvation fell from four to three deaths across these small six-game batches, while hazard deaths rose; this is diagnostic evidence, not a statistically established improvement.

In total, 39 real CLI matches were completed across development and final validation: 18 baseline-opponent matches and 21 self-play matches. The final implementation passed all 205 tests. Phase commits culminate in `06141c4`; the following documentation commit records these measured results. Restart the existing bot process on port 8000 to load the updated implementation. Temporary practice servers have been stopped.
