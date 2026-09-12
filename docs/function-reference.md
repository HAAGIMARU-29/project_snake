# Python function reference

[Documentation index](README.md)

Unless noted otherwise, functions are exported by [`main.py`](../main.py). A position is an `(x, y)` tuple, `blocked` is a set of positions, `state` is a game-state dictionary, and `direction` is one of `up`, `down`, `left`, or `right`. Functions expect valid inputs and do not serve as schema validators.

## Handlers and evaluation

| Function | Return and contract |
|---|---|
| `info()` | Metadata dictionary; logs `INFO` |
| `start(game_state)` | No return value; logs `GAME START`; no persistent state initialization |
| `move(game_state, search_enabled=None)` | `{'move': direction}`; environment supplies search default; owns deadlines and logging |
| `end(game_state)` | No return value; logs survival/elimination metadata |
| `score_move_components(game_state, move, blocked=None, strategic_weights=None)` | Dictionary of numeric heuristic contributions; hard-illegal move has negative-infinity safety; `search` initially zero |
| `evaluate_move(game_state, move, blocked=None, strategic_weights=None)` | Sum of the components; no tactical search |
| `log_decision(game_state, chosen, started, components, timed_out=False, fallback=False)` | Writes one JSON line unless per-move logging is disabled; `started` is an absolute `perf_counter` value |
| `death_reason(game_state)` | Evidence-based category string or `UNKNOWN` |

Both evaluation forms are supported:

```python
import main
from tests.fixtures import make_state

state = make_state(food=[{"x": 6, "y": 5}])
blocked = main.get_occupied_cells(state)
weights = main.build_strategic_weights(state)

simple = main.evaluate_move(state, "right")
precomputed = main.evaluate_move(state, "right", blocked, weights)
assert simple == precomputed
```

Pass precomputed structures from the same state. Evaluation copies occupancy, applies candidate tail release, opens the destination, and re-blocks the previous head. The strategic map should come from `build_strategic_weights`; arbitrary extra field features need corresponding component integration. It is not a generic externally supplied utility map.

## Coordinates and physical safety

| Function | Return and contract |
|---|---|
| `to_pos(cell)` | Tuple from `cell['x']`, `cell['y']` |
| `next_position(pos, move)` | Adds the direction delta; does not check bounds or collisions |
| `in_bounds(pos, width, height)` | Boolean rectangular bounds check |
| `get_occupied_cells(game_state)` | New set containing all board snake body coordinates |
| `get_effective_blocked_cells(game_state, candidate_move=None)` | New occupancy set; unique own tail may release only for a known non-eating candidate and body length ≥3 |
| `get_safe_moves(game_state, tail_aware=False)` | Ordered hard-safe directions; default preserves permanently occupied tails |
| `count_safe_exits(pos, blocked, width, height)` | Number of in-bounds unblocked neighbors, 0–4; does not test whether `pos` itself is free |

Safety sets and body lists are not mutated. Use `get_safe_moves(state, tail_aware=True)` when reproducing the live candidate list.

## Pathfinding

| Function | Return and contract |
|---|---|
| `bfs_distances(start, blocked, width, height)` | Reachable cell → shortest step count; source has distance zero; blocked/out-of-bounds source gives `{}` |
| `flood_fill_space(start, blocked, width, height, limit=None)` | Reachable cell count; blocked/out-of-bounds source gives 0; a positive `limit` permits early termination |
| `nearest_reachable_food_distance(distances, food)` | Minimum mapped distance to any supplied food, or `None` |
| `health_cost_distances(game_state, start, blocked, reverse=False)` | Dijkstra cost map including per-step hazard costs; reverse mode charges the destination edge needed for reverse food routing |

Flood fill with a positive limit reports only up to that threshold; do not interpret it as an exact region size. Without a limit, it counts the whole reachable region. Helpers never automatically remove a blocked source; callers must explicitly open a head when that is appropriate.

## Head threats and strategic fields

| Function | Return and contract |
|---|---|
| `initialize_strategic_weights(width, height)` | Dense position → 0.0 map for every board cell |
| `get_enemy_possible_head_positions(game_state, enemy_snake)` | Set of in-bounds current-occupancy-free enemy destinations; conservative about tails |
| `build_head_danger_map(game_state)` | Position → maximum threatening enemy length; adds possible unique-tail releases for pessimistic threat prediction |
| `build_strategic_weights(game_state, deadline=None)` | Dense combined head/food/immediate-hazard field; deadline passed to food builder |

The danger map carries lengths, not penalties. Compare with our body length before treating a threat as losing. The strategic map can contain keys for occupied cells; its existence never makes a cell physically legal.

## Food

| Function | Return and contract |
|---|---|
| `get_food_positions(game_state)` | Set of food positions, empty if none supplied |
| `get_dynamic_food_weight(health)` | One of 4.0, 30.0, 90.0, 240.0 |
| `build_food_attraction(game_state, blocked=None, danger=None, deadline=None)` | Sparse map of best food attraction per reachable cell; considers at most 12 BFS-ranked targets |
| `food_score_for_move(game_state, move, attraction=None)` | Raw food-field value at the candidate, before strategy-profile scaling |

Food scoring omits unreachable targets, discounts contested food and dead ends, and uses a health budget. The returned raw value is not necessarily identical to `components['food']`, which also applies the profile multiplier.

## Profiles, territory, and pressure

| Function | Return and contract |
|---|---|
| `get_strategy_profile(game_state)` | Dictionary with space, food, aggression, territory, derived head-pressure, and hazard weights |
| `compute_territory_map(game_state, blocked=None, our_start=None)` | Ownership map, our/enemy/contested sets, and normalized territory ratio |
| `aggression_score(game_state, destination, blocked, reachable, profile=None)` | Bounded bonus for the best shorter target; zero when its health/space/head/hazard gates fail |

Territory result keys are `ownership`, `our_territory`, `enemy_territory`, `contested_cells`, and `territory_ratio`. `ownership[cell]` is a snake ID or `None` for a tie; an absent key means unassigned or excluded. If `our_start` is supplied, our arrivals have a one-step offset. The output contains sets and tuple keys, so it is a Python debugging structure, not directly JSON-serializable.

## Royale

| Function | Return and contract |
|---|---|
| `is_royale(game_state)` | True only for exact ruleset name `royale` |
| `hazard_cells(game_state)` | Set of hazard cells in Royale; empty otherwise |
| `hazard_damage(game_state)` | Nonnegative requested damage, default 14 |
| `health_after_step(game_state, position, health=None)` | Food-aware health transition; defaults to our health but accepts another snake's health for simulation |
| `hazard_cost(game_state, position, hazards=None, food=None)` | Immediate strategic cost; optional sets avoid repeated extraction |
| `royale_score(game_state, position, blocked, distances)` | Immediate cost plus affordable safe-space reward or lack-of-access penalty |

`royale_score` currently accepts `distances` but computes its own energy distances; the supplied argument is not consumed. Preserve its call contract or update callers together if refactoring it.

## Search module

These functions are in [`snake/search.py`](../snake/search.py):

| Function | Return and contract |
|---|---|
| `simulate_turn(state, moves)` | Deep-copied next state and elimination reason map; moves keyed by snake ID |
| `plausible_responses(state, enemy)` | Nonempty direction list; includes potentially releasing tails |
| `response_penalty(state, our_id)` | 0, -1000, or -20000 based on next-step survival estimate |
| `choose_move(state, scores, fallback, deadline=None, enabled=True, clock=perf_counter)` | `(chosen_direction, penalty_map, timed_out)`; deadline and injected clock use the same monotonic time domain |

See [Search](search.md) for the exact horizon and fallback behavior.

## Inspect all candidate components

```python
import main
from tests.fixtures import make_state

state = make_state(food=[{"x": 6, "y": 5}])
blocked = main.get_occupied_cells(state)
weights = main.build_strategic_weights(state)

for direction in main.get_safe_moves(state, tail_aware=True):
    parts = main.score_move_components(state, direction, blocked, weights)
    print(direction, sum(parts.values()), parts)
```

Use a saved pre-move request for a loss diagnosis. Comparing components on the post-death board answers a different question because bodies, food, and hazards may already have changed.
