# Phase reports

The existing uncommitted bot and original 41 tests were preserved in commit `43e2a11`. Earlier test files were not edited. Every phase below passed the full pytest suite before the next began. Times are whole-suite wall times from that checkpoint, not per-move benchmarks.

| Phase | Files | Added functions / capabilities | Modified functions | Scoring | Added tests | Result | Runtime and limitations | Next |
|---|---|---|---|---|---|---|---|---|
| Baseline repair | main.py | Safe optional argument defaults | evaluate_move | No scoring changes | 0 | 41 pass; original baseline had 6 failures | ~0.20 s; static occupancy | Food |
| 4 | main.py, tests/test_phase4_food.py | get_food_positions, bfs_distances, nearest_reachable_food_distance, get_dynamic_food_weight, build_food_attraction, food_score_for_move, score_move_components | build_strategic_weights, evaluate_move | Bounded health-dependent food field, enemy-race discounts, starvation and hard-collision components | 19 | 60 pass | 0.13 s; static food paths | Tails |
| 5 | main.py, tests/test_phase5_tail.py | get_effective_blocked_cells | get_safe_moves, score_move_components, move | Candidate space includes unique own vacating tail | 8 | 68 pass | 0.10 s; enemy and stacked tails stay blocked | Profiles |
| 6 | main.py, tests/test_phase6_standard_strategy.py | get_strategy_profile | score_move_components | Four-alive survival weighting; increased territory and pressure as population falls | 7 | 75 pass | 0.12 s; territory/aggression weights activated in later phases | Territory |
| 7 | main.py, tests/test_phase7_territory.py | compute_territory_map | score_move_components | Our fraction of free cells; no bonus in a trap or losing head contest | 6 | 81 pass | 0.14 s; static Voronoi, tied arrivals contested | Royale |
| 8 | main.py, tests/test_phase8_royale.py | is_royale, hazard_cells, hazard_damage, health_after_step, hazard_cost, health_cost_distances, royale_score | build_food_attraction, build_strategic_weights, score_move_components | Health-budgeted hazard costs and accessible non-hazard space | 10 | 91 pass | 0.18 s; no random future shrink prediction | Aggression |
| 9 | main.py, tests/test_phase9_aggression.py | aggression_score | score_move_components | Safe shorter-enemy head pressure, food denial, exit denial, normalized space reduction | 8 | 99 pass | 0.18 s; one new chokepoint fixture corrected during development; prior tests untouched | Search |
| 10 | main.py, snake/__init__.py, snake/search.py, tests/test_phase10_search.py | simulate_turn, plausible_responses, response_penalty, choose_move | move | Worst-response death/trap penalty; optional search | 9 | 108 pass | 0.32 s; one simulated simultaneous turn plus next-exit check | Integration |
| Integration | tests/fixtures.py, tests/test_integration.py | integration_scenarios, body_at | None | None | 16 | 124 pass | 1.19 s; realistic fixtures, including 19×19 | Invariants |
| Invariants | tests/test_invariants.py | Fixed-seed valid-ish board generator | None | None | 40 | 164 pass | 2.98 s; deterministic and mutation checks | Performance |
| Performance | main.py, snake/search.py, tests/test_performance.py | Food target bound and tactical relevance bound | Food field, flood_fill_space, hazard_cost, search | Same rewards; at most 12 food targets | 15 | 179 pass | 2.07 s; fixed 5.9 s extreme-board failure and 168 ms 19×19 search; bounded flood checks | Hardening |
| 11 | main.py, scripts/practice.py, scripts/benchmark.py, tests/test_hardening.py, tests/test_baseline_regressions.py, requirements-dev.txt, .gitignore, reports/ | log_decision, death_reason; repeated match and benchmark runners | move, end, build_head_danger_map; deadline propagation | Vacating-tail contests remain dangerous; external weights cannot cancel fatal head penalty; Royale starvation uses energy distances; exit weight tuned 5→3 | 26 | 205 pass | Python 3.13.15; 4 upstream Flask deprecation warnings; measured rather than hard realtime guarantee | Live practice tuning |

Compatibility decisions:

- `evaluate_move(state, direction)` and `evaluate_move(state, direction, blocked, weights)` are both supported. Occupancy arguments are copied.
- `get_safe_moves(state)` keeps the original conservative contract, including the original test that treats our tail as blocked. Live play uses `get_safe_moves(state, tail_aware=True)`. The earlier test was not changed.
- Food and hazard fields are separate from physical occupancy. Shorter-head bonuses are gated evaluation components, so the Phase 3 strategic-weight contract remains intact.
- Actual simulated growth follows the engine's pop-tail-then-duplicate-new-tail order. Heuristic occupancy remains more conservative on eating moves, as requested.
- The installed Flask 2.3.2 convenience test client expects removed Werkzeug version metadata. The route regression uses Werkzeug's WSGI client against the actual unchanged Flask app. Real CLI matches also validate HTTP routing.
- No runtime dependencies were added. pytest is listed separately as a development dependency.
