# Strategy and scoring

[Documentation index](README.md) · [Implementation](../main.py)

## Score model

The heuristic score is the sum of these component keys:

```text
safety + space + exits + trap + head + food + starvation
       + territory + hazard + aggression + search
```

`search` is zero in `score_move_components` and `evaluate_move`. Live `move` applies the optional search result afterward. The score is a utility estimate, not a probability of survival or a predicted win rate.

The intended order is physical safety, space survival, head safety, health/food, and then positional strategy. The implementation combines hard rejection with penalties and gated rewards rather than sorting every component lexicographically. A possible head collision is a large soft penalty, whereas a wall or non-vacating body is rejected outright.

## Physical safety and tails

For each direction, compute the destination and reject it if it is outside the board or in effective occupancy.

Own-tail release requires all of the following:

1. A candidate move is known.
2. Our body has at least three segments.
3. The candidate destination is not food.
4. The tail coordinate occurs exactly once across every snake's body.

Enemy tails remain occupied for our move filter. Own tails remain occupied when eating, when stacked, or when shared by another body segment. Original lists are never edited. This heuristic is intentionally more conservative than the simulator's exact immediate growth order.

The legacy call `get_safe_moves(state)` does not release tails. Live play calls `get_safe_moves(state, tail_aware=True)`. This keeps the original Phase 1 collision tests meaningful without disabling tail following in actual games.

## Reachable space and exits

Evaluation blocks the old head, opens the legal candidate destination, and computes BFS distances from the destination. The number of visited cells is reachable space. A body's future movement is not simulated here.

Let `R` be reachable cells, `L` the current body length plus one if the destination is food, and `Pspace` the profile multiplier:

```text
space = min(R, 400) × 1.0 × Pspace
exits = count_safe_exits(destination) × 3.0
trap  = -1000 if R < L
        -500 if R / max(1, L) < 1.5
           0 otherwise
```

The 400-cell cap bounds positive rewards on larger boards. Territory is normalized by free cells; space deliberately retains the earlier count-based scoring with a cap. Reachability does not prove a non-self-intersecting route long enough to occupy every visited cell. A large region with a narrow entry can still be dangerous.

## Enemy head danger

The danger map stores the maximum enemy body length that could enter each cell next turn. Normal candidate cells must be in bounds and free of current bodies. Threat prediction additionally includes unique tail cells that could vacate, even though our own legal filter does not rely on enemy tails releasing.

If the maximum enemy length is at least ours, the candidate receives `-10000`. Shorter enemies do not receive an unconditional positive field weight. Any reward for pressuring them is separately gated by our health, space, and head safety.

Food routing also excludes equal/larger head-danger cells. That remains conservative for food many turns away: it treats a current threat cell as blocked throughout the route rather than forecasting when it becomes safe.

## Food and health

### Urgency

| Current health | Food urgency |
|---|---:|
| Above 70 | 4 |
| 41–70 | 30 |
| 21–40 | 90 |
| 20 or below | 240 |

### Target selection and route scoring

1. Extract food coordinates into a set.
2. Run BFS from our head through static occupancy with dangerous head cells excluded.
3. Rank reachable foods by BFS distance, then coordinates, and keep at most 12.
4. For each target, run reverse reachability from the food through the same conservative obstacles.
5. Ignore food whose reachable region has fewer than `current_length + 1` cells.
6. Scale region quality by `min(1, region_size / (1.5 × (current_length + 1)))`.
7. Multiply quality by 0.1 if the food has fewer than two free neighboring cells.
8. Compare our route length with BFS arrivals of equal/larger enemies. If any such enemy reaches the food no later than us, multiply attraction by 0.1.
9. Ignore routes whose steps or Royale energy cost exceed current health.

For a candidate cell and target food:

```text
steps = BFS distance from candidate to food + 1
attraction = urgency × quality × contest_factor / steps
```

The field uses the maximum attraction from any target, not a sum across foods. A dense food board therefore cannot create an arbitrarily large reward. The evaluation component extracts this food contribution from the combined strategic field, clamps it between zero and the current urgency, then applies the profile's food multiplier. Supplying an inflated field cannot cancel a fatal head penalty.

These target paths use static occupancy, even when candidate evaluation releases our tail. A route that becomes available only through a moving tail may therefore have understated attraction.

### Starvation

If the next step leaves health at or below zero, starvation contributes `-10000`. Otherwise, at health ≤20, a non-food move contributes `-1500` if no current food is reachable within the remaining budget. Standard uses BFS steps; Royale uses energy distances plus the immediate entry cost.

Immediate food resets health and avoids this starvation penalty. Future food spawns and chains of food-induced health resets are not planned. A lethal hazard can contribute both a lethal hazard score and an immediate health-death score; these named penalties are additive.

## Standard profiles

Profiles are derived from `len(board["snakes"])`:

| Alive | Space | Food | Territory | Aggression | Derived head pressure |
|---|---:|---:|---:|---:|---:|
| 4+ | 1.2 | 0.8 | 15 | 0.15 | 1.8 |
| 3 | 1.1 | 0.9 | 30 | 0.45 | 5.4 |
| 2 | 1.0 | 1.0 | 60 | 1.0 | 12 |
| 1 | 1.0 | 1.0 | 0 | 0 | 0 |

These profiles are also used in Royale; hazard handling adds another component. The hazard multiplier is always 1.0. Four-snake play emphasizes surviving with room to move. As snakes disappear, territory and shorter-enemy pressure become more influential.

`head_pressure_weight` is currently a derived profile value, not an independently consumed tuning knob. `aggression_score` adds a literal 12-point head term before multiplying by `aggression_weight`. Changing only the returned `head_pressure_weight` will not change decisions.

## Territory

`compute_territory_map` runs repeated BFS from our head and each enemy head. Each source can leave its own head cell; other blocked cells remain obstacles.

A free cell belongs to the uniquely earliest arrival. Equal arrivals are contested, including equal arrivals between enemies. Unreachable cells have no ownership entry. Length does not break ties in this implementation.

For candidate evaluation, our source is the candidate destination with an arrival offset of one. Enemies start from their current heads with offset zero. This avoids giving us a free simulated step in the race.

```text
territory_ratio = number of our owned free cells / max(1, free cells)
territory_component = territory_ratio × profile territory weight
```

The free-cell denominator includes free cells unreachable from every snake, and excludes in-bounds blocked cells. Territory contributes only when our trap and head components are both zero.

## Royale hazards

Only ruleset name `royale` activates hazard helpers. Hazard cells remain traversable physical space.

The implemented one-step health transition is:

```text
100                         if the destination contains food
health - 1 - hazard_damage   if it is a hazard without food
health - 1                  otherwise
```

Hazard damage comes from the request, defaults to 14, and is clamped to zero or above. A food cell has zero immediate hazard penalty. A non-food hazard has:

```text
-10000                                      if remaining health <= 0
-min(400, damage × (1 + 50 / remaining))      otherwise
```

Dijkstra routing prices one unit for a normal step and one plus hazard damage for a non-food hazard step. Reverse routing charges the appropriate destination edge for attraction toward food. These energy maps do not simulate multiple health resets along a route.

`royale_score` adds up to `25 × affordable_safe_cells / board_area`. A non-hazard cell must be reached with strictly positive remaining health to count. If neither safe space nor current food is affordable, it subtracts another 1500. The goal is accessible safe area rather than geometric center. Future random shrink events are not simulated.

## Controlled aggression

Pressure is considered only when our trap/head components are zero. The helper additionally requires health >40, at least `1.5 × (length + 1)` reachable cells, no equal/larger head threat, and no negative immediate hazard cost.

For each shorter enemy, compare reachable cells and immediate exits before and after blocking our destination. Subtract one from raw lost space so the destination cell itself is not counted as a strategic reduction.

```text
pressure = 60 × lost_space_fraction
         + 8 × lost_exits
         + 12 if we pressure an enemy next-head cell
         + 8 if that head pressure leaves at most one exit
         + 12 if we take food the enemy could reach within two steps
aggression = min(80, best target's pressure) × profile aggression multiplier
```

Pressure from multiple enemies is not summed. A local reduction is an opportunity estimate, not proof that the opponent can be killed.

## Constant locations

Named constants live near the top of [`main.py`](../main.py) and [`snake/search.py`](../snake/search.py). Several coefficients above are literal values inside helpers, including food bands, profile weights, hazard sensitivity, and aggression terms. See [Development and tuning](development.md) before changing them, and [Search](search.md) for the separate `-20000` tactical penalty and time budgets.
