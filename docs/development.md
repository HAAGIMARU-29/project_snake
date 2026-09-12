# Development, tuning, and implementation history

[Documentation index](README.md)

## Working on the project

The project is a hackathon extension of the official starter. Preserve the small server and the existing helper contracts. Add code where it belongs before considering another module: most strategy helpers currently live in `main.py`, while simultaneous simulation and search live in `snake/search.py`.

A normal behavior-change workflow is:

1. Inspect the affected implementation and tests.
2. Capture a concrete failing board or describe the desired decision change.
3. Make a small implementation change with focused regression coverage.
4. Run the relevant tests and then `.venv/bin/python -m pytest -q`.
5. Run the benchmark if work per move changed.
6. Use repeated Standard and Royale matches for strategic tuning.
7. Record constants, results, known limitations, and a logically isolated commit.

Do not change an earlier test merely to obtain a pass. If the test's model is demonstrably incorrect, explain the contradiction and the corrected expectation. The initial implementation preserved all original Phase 1–3 tests; `get_safe_moves(..., tail_aware=True)` is an example of adding behavior while retaining the old default contract.

Documentation changes should update affected guides and source links. Recorded reports are historical evidence; do not silently replace an older measured result with an unmeasured claim. When rerunning `scripts/benchmark.py`, remember that it overwrites the benchmark artifact.

## Rules for adding a feature

- Keep hard occupancy as a set and walls as bounds checks. Never represent a body collision only with a large negative field value.
- Keep flood-fill survival independent of strategic weights.
- Bound rewards so a strategic benefit cannot cancel a known fatal penalty.
- Preserve optional precomputed evaluation arguments and copy caller-owned sets before editing them.
- Do not mutate request bodies or keep mutable global game state.
- Use board dimensions and normalized territory/pressure fractions rather than 11×11-specific scoring thresholds.
- Add a named component when it makes a decision easier to diagnose. The current extraction from `strategic_weights` assumes head + food + immediate hazard; simply adding an unrelated field value can otherwise be mistaken for food.
- Search additions must preserve a usable heuristic fallback and cooperative deadline checks.
- Keep simultaneous simulation consistent with food, growth, health, bodies, and head collisions. Test script execution as well as imports when changing the `main`/search boundary.

## Tuning locations

| Parameter | Location | Why adjust it |
|---|---|---|
| `SPACE_WEIGHT`, `EXIT_WEIGHT` | Top of `main.py` | Balance room and local maneuverability |
| `TRAP_PENALTY`, `SPACE_RATIO_THRESHOLD` | Top of `main.py` | Increase or decrease aversion to small reachable regions |
| `HEAD_DANGER_PENALTY` | Top of `main.py` | Safety separation; retain a large margin over positive rewards |
| Food health bands | `get_dynamic_food_weight` | Earlier food pursuit or stronger emergencies |
| `FOOD_TARGET_LIMIT` | Top of `main.py` | Food quality/runtime tradeoff on dense boards |
| Population profile | `get_strategy_profile` | Survival versus territory/pressure as opponents disappear |
| Hazard sensitivity and safe-access bonus | `hazard_cost`, `royale_score` | Health-dependent willingness to cross hazards |
| Pressure coefficients/gates | `aggression_score` | Food denial and shorter-opponent opportunities |
| Search budgets/relevance | Top of `snake/search.py` | Runtime margin and tactical response coverage |

Many coefficients are literal values inside these functions, not environment-configurable settings. `head_pressure_weight` is currently descriptive: aggression uses a literal 12 multiplied by `aggression_weight`. Edit the consumed expression if introducing an independent head-pressure control.

## A disciplined tuning experiment

Change one parameter at a time and retain the previous revision. Compare a mix of seeds, board sizes, and opponents. Track survival turns and engine death causes alongside wins; self-play always produces losses for some identical copies and does not independently establish competitive strength.

A useful experiment record includes:

```text
Revision:
Parameter before / after:
Reason for change:
Saved regression state, if any:
Test result:
Benchmark mean / P95 / maximum:
CLI mode, size, seeds, opponent revision:
Wins, survival turns, death causes:
Decision: retain / revert / collect more evidence
```

The hardening pass reduced `EXIT_WEIGHT` from 5 to 3 after examining starvation losses and also corrected Royale starvation checks to use existing energy-distance routing. The final six self-play games had three starvation deaths versus four in the preceding six-game batch, but hazard deaths rose. This sample is too small and has too many coupled game effects to claim a statistically established improvement.

## Current limitations and extension opportunities

| Limitation | Consequence |
|---|---|
| Static bodies beyond immediate own-tail release | Reachability and food paths can reject a future opening or miss later self-enclosure |
| Conservative enemy tails | Some legal emergency escapes are rejected |
| Current head-danger cells excluded along whole food paths | Food routes can be more pessimistic than time-aware routing would be |
| Twelve food targets and no multi-food reset planning | Some distant or chained feeding routes are not considered |
| Flood-fill size is not path capacity | A region with many cells can still have a fatal bottleneck |
| Static Voronoi | Territory is an estimate, not a guarantee against moving opponents |
| One simulated turn plus next-exit check | Multi-turn squeezes and traps can be missed |
| Representative distant-enemy responses | Search is not exhaustive multiplayer minimax |
| No future food spawn or random shrink simulation | Plans may be invalidated by later Royale changes |
| Standard/Royale-specific implementation | Wrapped, squad, constrictor, and other variants need explicit support |
| Cooperative deadlines | Bounded operations and host scheduling can overrun a nominal cutoff slightly |
| Partial elimination metadata | `/end` can produce UNKNOWN; engine artifacts are needed for exact causes |

These are potential future tasks, not features currently implemented. The hackathon hardening rule was to stop adding major algorithms once instrumentation and practice began.

## Implementation milestones

| Checkpoint | Commit | Outcome |
|---|---|---|
| Preserve starting bot/tests | `43e2a11` | Existing Phase 1–3 implementation saved |
| Repair evaluation arguments | `25b0cd6` | Both evaluation call forms work; baseline used by practice runner |
| Phase 4 | `83bf7e5` | Health-aware BFS food and component scoring |
| Phase 5 | `2dbfef9` | Candidate-aware own-tail occupancy |
| Phase 6 | `39f6788` | Player-count strategy profiles |
| Phase 7 | `fa46f5f` | Normalized BFS territory |
| Phase 8 | `b463d18` | Royale hazard energy and safe-space access |
| Phase 9 | `9220df3` | Controlled pressure and denial |
| Phase 10 | `d15cfa2` | Deadline-limited tactical search |
| Integration/invariants | `e9f6e35`, `cedebe6` | Scenario and fixed-seed mutation/safety coverage |
| Performance | `95bcdf9` | Food target bound, tactical relevance, and bounded flood checks |
| Phase 11 | `06141c4` | Telemetry, practice tools, safety fixes, and tuning |
| Recorded handoff | `4c89a5a` | Phase report, 205-test result, benchmarks, and 39 CLI matches |

See the [phase report](../reports/PHASE_REPORT.md) for functions changed and test counts at each step. The [original MIT license](../LICENSE) remains in the repository.
