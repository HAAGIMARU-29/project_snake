# Minimax, Alpha-Beta, and MaxN implementation plan

[Documentation index](README.md) · [Current search](search.md) · [Strategy](strategy-and-scoring.md)

This plan extends the existing bot in controlled steps. The current implementation remains the fallback at every stage. A search result is used only when it completes at least one full depth and returns a legal move.

## Implementation status

The plan is now implemented through the tournament-hardening baseline. M1 search foundations, M2 two-player Alpha-Beta, M3 multi-player MaxN, M4 simultaneous-turn simulation fidelity, and M5 bounded performance controls are live and covered by tests. M6 validation is the ongoing practice loop: the automated suite and local benchmark are repeatable, while live CLI match statistics should continue to guide constant tuning.

The production implementation intentionally keeps the request dictionary as its state format. It uses local fingerprints and bounded branching rather than introducing a second compact engine state, which preserves the starter API and keeps the change set small enough for the hackathon deadline.

## Goals and constraints

- Improve tactical decisions with full-turn look-ahead.
- Use iterative deepening and return the best move from the last completed depth.
- Use Alpha-Beta only for a two-player search frame: us versus one fully simulated relevant opponent.
- Use MaxN when more than two snakes are fully simulated; each player owns one utility component and chooses the action maximizing that component.
- Gate fully simulated opponents by their distance to our head and by whether their body can enter the tactical neighborhood within the search horizon.
- Preserve deterministic tie-breaking, hard occupancy, food/hazard rules, input immutability, and the existing `move()` JSON contract.
- Keep normal decisions below 50 ms, P95 below 100 ms, and the existing cooperative cutoff around 270 ms.

The reference material is used for the algorithm split and opponent relevance idea. The AWS SageMaker Battlesnake repository is primarily an RL training/deployment framework, so this project will borrow its environment-oriented separation without adding SageMaker, ML, or runtime dependencies. See the reference links at the end of this document.

## Non-goals

- Deep multiplayer minimax over every snake on the board.
- Neural networks, Monte Carlo Tree Search, or a database.
- Replacing the validated heuristic scorer in one edit.
- Claiming a search result is correct when the deadline interrupts a depth.
- Assuming a future food spawn or random Royale shrink that is not present in the request.

## Target architecture

```text
main.move
  ├─ hard-safe candidate generation
  ├─ heuristic score components and fallback
  └─ search controller
       ├─ compact immutable search state
       ├─ relevant-opponent selection
       ├─ deterministic move ordering
       ├─ iterative deepening controller
       ├─ two-player Alpha-Beta / Negamax
       └─ N-player MaxN
```

The controller owns the deadline and records the last completed depth. Search functions return a structured result containing the move, score/vector, completed depth, nodes, and timeout flag. The existing `choose_move()` tuple remains supported during migration.

## Phase M1 — search foundation (implemented)

1. Add a pure `SearchResult` representation and a monotonic deadline helper.
2. Add `select_relevant_snakes(state, max_distance, horizon)` using the minimum Manhattan distance from any enemy body segment to our head. Always include an enemy that can enter our current head neighborhood within the horizon; never simulate a distant enemy merely because it exists.
3. Add deterministic per-snake legal move generation that uses the existing hard occupancy and candidate tail rules.
4. Add a root-perspective state evaluator that reuses the existing safety, space, health, food, territory, hazard, and length signals without mutating the request.
5. Add focused tests for relevance, legal move generation, deadline checks, and evaluation invariants.

Exit criteria met: helpers are deterministic, do not mutate requests, and remain under the performance budget.

## Phase M2 — two-player Alpha-Beta (implemented)

1. Define a search ply as one complete simultaneous game turn.
2. Search our root move, then the relevant opponent's response moves. The opponent minimizes our root utility.
3. Apply deterministic move ordering: hard-safe moves first, then heuristic score, head safety, food, space, and the established move priority.
4. Implement Alpha-Beta recursion with a transposition table keyed by a canonical state fingerprint, side-to-move, and remaining depth. Completed values are cached locally to the request.
5. Add iterative deepening from depth 1 through a board-size/population-dependent maximum. If depth N is interrupted, discard that partial result and keep depth N−1.
6. Integrate when exactly one relevant opponent is fully simulated. Retain the current one-turn search as the migration safety gate.

The two-player value must be root-relative. Negamax is acceptable internally, but no sign conversion may be applied to a multi-player node.

## Phase M3 — N-player MaxN (implemented)

1. Build a player list containing us and every relevant fully simulated enemy.
2. At each node, the player whose turn is being expanded chooses the child with the largest value in that player's vector component.
3. Return a vector for every player, with our component including survival, space, health/food, territory, and safe tactical position; enemy components use their own survival, space, health, food access, and pressure estimate.
4. Do not apply Alpha-Beta cutoffs to MaxN nodes. Use move ordering, transposition reuse, relevance gating, depth limits, and terminal pruning instead.
5. For snakes outside the relevant set, use a deterministic reflex move or a conservative environmental approximation at leaf evaluation. Document which approximation was used.
6. Integrate MaxN only when more than two snakes are fully simulated.

MaxN is intentionally shallower. A four-snake tree with four actions each grows roughly as `4^(players × depth)` before pruning, so the deadline controller must prefer a completed shallow MaxN depth over a partial deeper depth.

## Phase M4 — simulation fidelity (implemented baseline)

Before trusting deeper search, harden `simulate_turn`:

- Correctly release or retain each tail based on that snake's food result.
- Apply health decrement, food reset, hazard damage, and Royale elimination in engine order.
- Resolve wall, body, self, and head-to-head collisions from the same simultaneous post-move state.
- Preserve all snakes' IDs and update `you` only for the root perspective.
- Keep food and body data isolated from the caller.
- Add tests for multiple snakes choosing the same food, equal head collisions, growth, hazards, and bodies that vacate simultaneously.

The baseline simulation tests pass. Additional engine replay fixtures remain useful before increasing the default depth.

## Phase M5 — performance engineering (implemented baseline)

- Keep the request dictionary stable and use local fingerprints; compact immutable tuples remain an optional future optimization.
- Precompute board geometry, static hazard masks, and coordinate indexes per search call.
- Use reversible apply/undo when correctness tests prove it safer than copying.
- Cap branching with legal-move filtering, relevant enemies, forced-move detection, and tactical move ordering.
- Keep transposition tables local to a single request; never use mutable match-global caches.
- Measure nodes, cache hits, completed depth, and search time in telemetry.
- Benchmark Standard 11×11, crowded late-game Standard, Royale 11×11, Royale 19×19, long snakes, and many-food boards.

The current implementation improves tactical regression coverage while staying below the internal cutoff in the representative local benchmark. A slower deeper result that loses the timeout margin is still a regression.

## M6 — validation and tuning (in progress during practice)

Add tests in this order:

1. `test_minimax_foundation.py`: relevance, state fingerprints, deadline, legal moves, evaluation, no mutation.
2. `test_alpha_beta.py`: depth completion, bounds, transposition correctness, immediate tactical death, deterministic ordering, timeout fallback.
3. `test_maxn.py`: vector shape, player-specific choices, no Alpha-Beta pruning at MaxN nodes, three/four-snake deterministic results.
4. `test_search_integration.py`: `move()` chooses a search-improved legal move and preserves heuristic behavior when disabled.
5. Extend integration and performance tests with node/depth telemetry assertions.

For every change, run the full suite, then the benchmark, then repeated Standard and Royale CLI matches. Compare death causes and survival turns, not wins alone. Tune one value at a time, preserving a regression fixture for every tactical improvement.

## Proposed APIs

```python
select_relevant_snakes(game_state, max_distance=4, horizon=2)
fingerprint_state(game_state, perspective_id)
generate_search_moves(game_state, snake_id, ordering_scores=None)
evaluate_search_state(game_state, root_id, player_ids=None)
alpha_beta_root(game_state, root_id, opponent_id, depth, deadline, table)
maxn_root(game_state, player_ids, depth, deadline, table)
iterative_deepening_search(game_state, fallback, deadline, enabled=True)
```

Names may change during implementation, but the contracts should remain small and testable. `iterative_deepening_search` should return a result like:

```python
{
    "move": "up",
    "score": 123.4,
    "completed_depth": 2,
    "nodes": 418,
    "cache_hits": 37,
    "timed_out": False,
    "algorithm": "alphabeta",  # or "maxn", "fallback"
}
```

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Search chooses a technically legal but strategically losing line | Keep heuristic terminal evaluation, head danger, trap penalties, and next-exit checks in every leaf |
| MaxN tree explodes with four snakes | Distance/horizon gating, shallow completed depths, forced moves, ordering, local tables |
| Alpha-Beta is incorrectly applied to N players | Separate dispatch and recursion functions; assert player count in tests |
| Partial depth biases move choice | Store and return only the last completed iteration |
| Deep-copy simulation consumes the budget | Measure first, then introduce compact state and/or apply/undo with mutation tests |
| Search simulation disagrees with the engine | Use CLI replay fixtures and engine death causes before raising depth |
| A transposition key omits a rule-relevant field | Include dimensions, ruleset, hazards, food, health, bodies, root ID, and turn-relevant search state |
| New search breaks the starter API | Preserve `move()`, `server.py`, optional `evaluate_move` arguments, and disabled-search behavior |

## Reference material

- [AWS Labs SageMaker Battlesnake AI](https://github.com/awslabs/sagemaker-battlesnake-ai): RL environment, inference, deployment, and heuristic integration reference. It is not a runtime dependency for this bot.
- [Battlesnake Challenge paper](https://arxiv.org/abs/2007.10504): describes the multi-agent Battlesnake setting and the AWS framework.
- [Team write-up describing distance-gated Alpha-Beta and MaxN](https://github.com/m-schier/battlesnake-2019): reference for simulating nearby opponents, using Alpha-Beta for two fully simulated snakes, and MaxN for more than two.
- [Official Battlesnake rules implementation](https://github.com/BattlesnakeOfficial/rules): reference for movement, growth, health, hazards, and collision order.

## Decision gate after each phase

Do not increase depth or enable a new algorithm in live play until:

- the phase-specific tests and the full existing suite pass;
- the move remains deterministic and does not mutate input state;
- the fallback remains legal when the deadline is already expired;
- benchmark P95 remains below the project target;
- a CLI replay demonstrates a concrete tactical improvement or confirms no regression.
