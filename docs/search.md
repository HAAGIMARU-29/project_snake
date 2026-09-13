# Tactical search and deadlines

[Documentation index](README.md) · [Implementation](../snake/search.py)

The live search path is iterative deepening over complete simultaneous turns. It dispatches to Alpha-Beta for one relevant opponent and MaxN for multiple relevant opponents. The original bounded one-turn response search remains available as a compatibility safety gate during migration.

## Scope

Search models complete simultaneous turns recursively. At each completed depth it retains the best legal root move; if the deadline interrupts the next depth, that partial iteration is discarded. MaxN is deliberately shallower than the two-player Alpha-Beta path because it evaluates a utility vector for every fully simulated player.

The entry point is:

```python
chosen, penalties, timed_out = choose_move(
    state, scores, fallback, deadline=None, enabled=True
)
```

`scores` maps candidate directions to heuristic totals. The caller must supply suitable candidate moves and a valid fallback. With search disabled or no scores, the helper returns `(fallback, {}, False)`.

The iterative controller is:

```python
result = iterative_deepening_search(
    state, fallback, deadline, enabled=True, max_depth=2
)
```

`SearchResult` reports `move`, `score`, `completed_depth`, `nodes`, `cache_hits`, `timed_out`, `algorithm`, and (for MaxN) the utility `vector`.

## Response generation

For each enemy, `plausible_responses` first uses tail-aware safety from that enemy's perspective. It then adds in-bounds moves into unique tail cells that might release. This deliberately includes possibilities our own conservative filter would not choose. If no response is generated, it returns `['up']` so simulation still has a direction.

Enemies whose current head is within four Manhattan grid steps of ours get all plausible responses enumerated. More distant enemies get one representative response, the first in their deterministic list. The distance is a tactical relevance bound: two simultaneous turns can close at most four grid steps. Food routing still uses actual BFS, not this Manhattan bound.

The recursive search gates fully simulated opponents with `select_relevant_snakes`: distance from our head to the enemy body is compared with the tactical horizon. Distant snakes contribute a deterministic reflex move at the leaf instead of multiplying the tree. Branching is also capped after deterministic safety and heuristic ordering (`MAX_ORDERED_ACTIONS` for two-player nodes and `MAX_MAXN_ACTIONS` for MaxN nodes).

For one relevant opponent, Alpha-Beta treats us as the maximizing player and that opponent as the minimizing player over simultaneous-turn transitions. For multiple relevant opponents, MaxN selects the child that maximizes the acting player's component of the returned utility vector; it intentionally applies no Alpha-Beta cutoff.

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

If the deadline is already expired, search returns the supplied heuristic fallback at depth zero. If a later iterative-deepening depth times out, the result from the last completed depth is returned with `timed_out=True`; a partial deeper result is never promoted. If heuristic evaluation itself was cut short, that fallback is the best of the candidates completed so far.

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

Tests cover expired and mid-search deadlines, last-completed-depth fallback, Alpha-Beta cache reuse, MaxN vector selection, legality, mutation, simulation, head collisions, and a saved [tactical regression state](../tests/tactical_regression.json) where the real heuristic chooses `up` but search selects `down` to avoid a worse response.
