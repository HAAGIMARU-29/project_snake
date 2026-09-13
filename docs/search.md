# Tactical search and deadlines

[Documentation index](README.md) · [Implementation](../snake/search.py)

The next search expansion is tracked in the [Minimax, Alpha-Beta, and MaxN plan](minimax-plan.md). The current production path remains the bounded one-turn search described below until each deeper-search phase passes its dedicated tests.

## Scope

Search adds one simultaneous turn of enemy-response modeling to the heuristic, then examines our available next-step exits. It is a bounded worst-response approximation. It does not recursively run full multiplayer minimax or search an arbitrary depth.

The entry point is:

```python
chosen, penalties, timed_out = choose_move(
    state, scores, fallback, deadline=None, enabled=True
)
```

`scores` maps candidate directions to heuristic totals. The caller must supply suitable candidate moves and a valid fallback. With search disabled or no scores, the helper returns `(fallback, {}, False)`.

## Response generation

For each enemy, `plausible_responses` first uses tail-aware safety from that enemy's perspective. It then adds in-bounds moves into unique tail cells that might release. This deliberately includes possibilities our own conservative filter would not choose. If no response is generated, it returns `['up']` so simulation still has a direction.

Enemies whose current head is within four Manhattan grid steps of ours get all plausible responses enumerated. More distant enemies get one representative response, the first in their deterministic list. The distance is a tactical relevance bound: two simultaneous turns can close at most four grid steps. Food routing still uses actual BFS, not this Manhattan bound.

For three nearby enemies, each with at most four directions, the Cartesian product has at most 64 response combinations per our candidate, or 256 immediate simulations across four candidates before pruning. With no enemies, the empty product still yields one simulation per candidate.

## Simulation sequence

`simulate_turn(state, moves)` deep-copies the state, where `moves` maps snake IDs to directions. Missing move entries default to `up`.

1. Compute each new head and remove the previous tail.
2. Apply one-step health, including food reset and Royale damage.
3. If food is eaten, duplicate the new body's last segment to represent immediate growth.
4. Record wall and health eliminations.
5. Check surviving bodies for self/body collisions and length-based head collisions. Equal-length head collisions eliminate both; collision decisions are collected before removing those snakes.
6. Remove eliminated snakes and eaten food, increment turn, and update `you` to the surviving simulated snake when present.

The result is `(future_state, reasons_by_snake_id)`. If our snake dies, `future_state['you']` can still hold its copied dead representation. Check the reasons or membership in `future_state['board']['snakes']` to determine survival.

The simulator does not create new food, add new hazards, or implement every external ruleset. Its immediate growth model is more precise than the conservative own-tail occupancy rule used for selecting our candidate moves.

## Evaluating responses

`response_penalty` returns:

| Condition | Penalty |
|---|---:|
| Our snake eliminated | -20,000 |
| No next move with positive space that avoids immediate health/head danger | -20,000 |
| Best available next region smaller than our current simulated length | -1,000 |
| A next safe region reaches at least that length | 0 |

It uses flood fill with `limit=length`, stopping as soon as enough space is found. It does not compute a complete future heuristic score or fully simulate a second simultaneous turn. In particular, a possible next head threat is treated pessimistically even if the opponent might choose otherwise.

For each our candidate, search retains the minimum response penalty. Once a `-20000` response is found, further responses for that candidate are pruned. On completion, it maximizes:

```text
heuristic_score[direction] + worst_response_penalty[direction]
```

Ties use `up`, `right`, `down`, `left`. Search only adds non-positive penalties; it can expose a tactical problem rather than add another large attack reward.

## Budgets and fallback

| Control | Value |
|---|---:|
| `SEARCH_BUDGET_SECONDS` | 0.22 |
| `HARD_CUTOFF_SECONDS` | 0.27 |
| `SEARCH_DEATH_PENALTY` | 20,000 |
| `RELEVANT_ENEMY_DISTANCE` | 4 |

The live decision sets an absolute `perf_counter()` deadline:

```text
decision_deadline = start + min(0.27, max(0.001, timeout_seconds × 0.6))
search_deadline = min(decision_deadline, search_start + 0.22)
```

A standard 500 ms request therefore gives a nominal 270 ms internal decision budget. A 100 ms request gives 60 ms. Food-field construction checks its deadline between food targets. Heuristic evaluation checks between candidates after computing at least one. Search checks before starting, between response combinations, and before returning.

If tactical search reaches its deadline, it returns the supplied heuristic fallback, an empty penalty map, and `True`. Partial tactical results are discarded to avoid favoring candidates evaluated earlier. If heuristic evaluation itself was cut short, that fallback is the best of the candidates completed so far.

The cutoff is cooperative, not a preemptive watchdog: an individual BFS, simulation, JSON log write, or OS scheduling delay can extend wall time. Completed decisions are deterministic on identical states; the amount of work completed at a real deadline can vary with host load.

## Disabling and inspecting search

```python
import main
from tests.fixtures import make_state

state = make_state()
heuristic_response = main.move(state, search_enabled=False)
searched_response = main.move(state, search_enabled=True)
```

The explicit argument overrides the environment switch. Without an explicit argument, `BATTLESNAKE_SEARCH=0` disables search.

The chosen move's logged `scores.search` contains its adjustment. `search_timeout` reports tactical deadline exhaustion; `fallback` separately reports the no-hard-safe-move fallback. Neither field is a general network-timeout detector.

Tests cover expired and mid-search deadlines, legality, mutation, simulation, head collisions, and a saved [tactical regression state](../tests/tactical_regression.json) where the real heuristic chooses `up` but search selects `down` to avoid a worse response.
