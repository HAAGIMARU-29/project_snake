# Welcome to
# __________         __    __  .__                               __
# \______   \_____ _/  |__/  |_|  |   ____   ______ ____ _____  |  | __ ____
#  |    |  _/\__  \\   __\   __\  | _/ __ \ /  ___//    \\__  \ |  |/ // __ \
#  |    |   \ / __ \|  |  |  | |  |_\  ___/ \___ \|   |  \/ __ \|    <\  ___/
#  |________/(______/__|  |__| |____/\_____>______>___|__(______/__|__\\_____>
#
# This file can be a nice home for your Battlesnake logic and helper functions.
#
# To get you started we've included code to prevent your Battlesnake from moving backwards.
# For more info see docs.battlesnake.com

import json
import os
import typing
from time import perf_counter
from snake.search import (
    choose_move,
    iterative_deepening_search,
    select_relevant_snakes,
    SEARCH_BUDGET_SECONDS,
    HARD_CUTOFF_SECONDS,
)
from collections import Counter, deque
from heapq import heappop, heappush


DIRECTIONS = {
    "up": (0, 1),
    "down": (0, -1),
    "left": (-1, 0),
    "right": (1, 0),
}

MOVE_PRIORITY = ["up", "right", "down", "left"]

SPACE_WEIGHT = 1.0
EXIT_WEIGHT = 3.0
TRAP_PENALTY = 1000.0
SPACE_RATIO_THRESHOLD = 1.5

BASE_CELL_WEIGHT = 0.0
HEAD_DANGER_PENALTY = 10000.0
SHORTER_ENEMY_HEAD_BONUS = 0.0
FOOD_TARGET_LIMIT = 12


def to_pos(cell: typing.Dict) -> typing.Tuple[int, int]:
    return (cell["x"], cell["y"])


def next_position(pos: typing.Tuple[int, int], move: str) -> typing.Tuple[int, int]:
    dx, dy = DIRECTIONS[move]
    return (pos[0] + dx, pos[1] + dy)


def in_bounds(pos: typing.Tuple[int, int], width: int, height: int) -> bool:
    x, y = pos
    return 0 <= x < width and 0 <= y < height


def get_occupied_cells(game_state: typing.Dict) -> typing.Set[typing.Tuple[int, int]]:
    occupied = set()
    for snake in game_state.get("board", {}).get("snakes", []):
        for segment in snake.get("body", []):
            occupied.add(to_pos(segment))
    return occupied


def get_safe_moves(game_state: typing.Dict, tail_aware: bool = False) -> typing.List[str]:
    my_head = to_pos(game_state["you"]["body"][0])
    width = game_state["board"]["width"]
    height = game_state["board"]["height"]
    occupied = get_occupied_cells(game_state)

    safe = []
    for move in MOVE_PRIORITY:
        next_pos = next_position(my_head, move)
        effective = get_effective_blocked_cells(game_state, move) if tail_aware else occupied
        if in_bounds(next_pos, width, height) and next_pos not in effective:
            safe.append(move)
    return safe


def get_effective_blocked_cells(game_state, candidate_move=None):
    """Release only a unique own tail, on a known non-eating candidate.

    Enemy tails stay occupied: their food choice and growth are uncertain.
    Duplicate tails (growth / initial stacking) never open a false passage.
    """
    occupied = get_occupied_cells(game_state)
    body = game_state["you"]["body"]
    if candidate_move is None or len(body) < 3:
        return occupied
    destination = next_position(to_pos(body[0]), candidate_move)
    if destination in get_food_positions(game_state):
        return occupied
    tail = to_pos(body[-1])
    occurrences = sum(to_pos(cell) == tail for snake in game_state["board"]["snakes"]
                      for cell in snake["body"])
    if occurrences == 1:
        occupied.discard(tail)
    return occupied


def flood_fill_space(start: typing.Tuple[int, int], blocked: typing.Set[typing.Tuple[int, int]], width: int, height: int, limit=None) -> int:
    if start in blocked or not in_bounds(start, width, height):
        return 0

    visited = set([start])
    queue = deque([start])
    count = 0

    while queue:
        current = queue.popleft()
        count += 1
        if limit is not None and count >= limit:
            return count
        x, y = current

        for dx, dy in DIRECTIONS.values():
            neighbor = (x + dx, y + dy)
            if in_bounds(neighbor, width, height) and neighbor not in blocked and neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return count


def count_safe_exits(pos: typing.Tuple[int, int], blocked: typing.Set[typing.Tuple[int, int]], width: int, height: int) -> int:
    exits = 0
    for dx, dy in DIRECTIONS.values():
        neighbor = (pos[0] + dx, pos[1] + dy)
        if in_bounds(neighbor, width, height) and neighbor not in blocked:
            exits += 1
    return exits


def initialize_strategic_weights(width: int, height: int) -> typing.Dict[typing.Tuple[int, int], float]:
    weights = {}
    for x in range(width):
        for y in range(height):
            weights[(x, y)] = BASE_CELL_WEIGHT
    return weights


def get_enemy_possible_head_positions(game_state: typing.Dict, enemy_snake: typing.Dict) -> typing.Set[typing.Tuple[int, int]]:
    head = to_pos(enemy_snake["body"][0])
    width = game_state["board"]["width"]
    height = game_state["board"]["height"]
    occupied = get_occupied_cells(game_state)

    possible = set()
    for dx, dy in DIRECTIONS.values():
        candidate = (head[0] + dx, head[1] + dy)
        if in_bounds(candidate, width, height) and candidate not in occupied:
            possible.add(candidate)
    return possible


def build_head_danger_map(game_state: typing.Dict) -> typing.Dict[typing.Tuple[int, int], int]:
    danger_map = {}
    our_id = game_state.get("you", {}).get("id", "me")
    counts = Counter(to_pos(cell) for snake in game_state["board"]["snakes"] for cell in snake["body"])
    releasable = {to_pos(snake["body"][-1]) for snake in game_state["board"]["snakes"]
                  if len(snake["body"]) > 2 and counts[to_pos(snake["body"][-1])] == 1}

    for snake in game_state.get("board", {}).get("snakes", []):
        if snake.get("id") == our_id:
            continue
        enemy_length = len(snake.get("body", []))
        possible_positions = get_enemy_possible_head_positions(game_state, snake)
        # Threat prediction is deliberately more pessimistic than our legal filter.
        head = to_pos(snake["body"][0])
        possible_positions |= {next_position(head,direction) for direction in MOVE_PRIORITY
                               if next_position(head,direction) in releasable}
        for pos in possible_positions:
            if pos not in danger_map or enemy_length > danger_map[pos]:
                danger_map[pos] = enemy_length
    return danger_map


def build_strategic_weights(game_state: typing.Dict, deadline=None) -> typing.Dict[typing.Tuple[int, int], float]:
    width = game_state["board"]["width"]
    height = game_state["board"]["height"]
    our_length = len(game_state["you"]["body"])

    weights = initialize_strategic_weights(width, height)
    danger_map = build_head_danger_map(game_state)

    for pos, max_enemy_length in danger_map.items():
        if max_enemy_length >= our_length:
            weights[pos] -= HEAD_DANGER_PENALTY
        else:
            weights[pos] += SHORTER_ENEMY_HEAD_BONUS
    for pos, value in build_food_attraction(game_state, danger=danger_map, deadline=deadline).items():
        weights[pos] += value
    hazards, food = hazard_cells(game_state), get_food_positions(game_state)
    for pos in hazards:
        if pos in weights:
            weights[pos] += hazard_cost(game_state, pos, hazards, food)
    return weights


def aggression_score(game_state, destination, blocked, reachable, profile=None):
    """Small bonuses for verified pressure on shorter enemies only."""
    you, board = game_state["you"], game_state["board"]
    length = len(you["body"])
    if (you.get("health",100) <= 40 or reachable < SPACE_RATIO_THRESHOLD * (length + 1)
            or build_head_danger_map(game_state).get(destination,0) >= length
            or hazard_cost(game_state,destination) < 0):
        return 0.0
    profile = get_strategy_profile(game_state) if profile is None else profile
    width,height = board["width"],board["height"]
    best = 0.0
    for enemy in board["snakes"]:
        if enemy["id"] == you["id"] or len(enemy["body"]) >= length:
            continue
        head = to_pos(enemy["body"][0])
        before_blocked = set(blocked) - {head,destination}
        before = bfs_distances(head,before_blocked,width,height)
        after_blocked = before_blocked | {destination}
        after = bfs_distances(head,after_blocked,width,height)
        reduction = max(0,len(before)-len(after)-1) / max(1,width*height)
        exits_before = count_safe_exits(head,before_blocked,width,height)
        exits_after = count_safe_exits(head,after_blocked,width,height)
        denial = max(0,exits_before-exits_after)
        pressure = 60.0 * reduction + 8.0 * denial
        if destination in get_enemy_possible_head_positions(game_state,enemy):
            pressure += 12.0
            if exits_after <= 1:
                pressure += 8.0  # genuine restricted escape, often at an edge
        if destination in get_food_positions(game_state) and before.get(destination,99) <= 2:
            pressure += 12.0
        best = max(best,pressure)
    return min(80.0,best) * profile["aggression_weight"]


def is_royale(game_state):
    return game_state.get("game", {}).get("ruleset", {}).get("name") == "royale"


def hazard_cells(game_state):
    return {to_pos(cell) for cell in game_state["board"].get("hazards", [])} if is_royale(game_state) else set()


def hazard_damage(game_state):
    return max(0, game_state.get("game", {}).get("ruleset", {}).get("settings", {}).get("hazardDamagePerTurn", 14))


def health_after_step(game_state, position, health=None):
    health = game_state["you"].get("health",100) if health is None else health
    if position in get_food_positions(game_state):
        return 100
    return health - 1 - (hazard_damage(game_state) if position in hazard_cells(game_state) else 0)


def hazard_cost(game_state, position, hazards=None, food=None):
    hazards = hazard_cells(game_state) if hazards is None else hazards
    food = get_food_positions(game_state) if food is None else food
    if position not in hazards:
        return 0.0
    remaining = 100 if position in food else game_state["you"].get("health",100) - 1 - hazard_damage(game_state)
    if remaining <= 0:
        return -HEAD_DANGER_PENALTY
    if position in food:
        return 0.0
    return -min(400.0, hazard_damage(game_state) * (1.0 + 50.0 / remaining))


def health_cost_distances(game_state, start, blocked, reverse=False):
    """Dijkstra energy to the first food/safe region; no speculative food respawn.

    Reverse mode prices the destination edge, for food attraction fields.
    Food resets health when actually entered, handled by health_after_step.
    """
    board = game_state["board"]
    width, height = board["width"], board["height"]
    if start in blocked or not in_bounds(start,width,height):
        return {}
    hazards, food = hazard_cells(game_state), get_food_positions(game_state)
    damage = hazard_damage(game_state)
    costs = {start:0}
    queue = [(0,start)]
    while queue:
        cost, cell = heappop(queue)
        if cost != costs[cell]:
            continue
        for dx,dy in DIRECTIONS.values():
            neighbor = cell[0]+dx,cell[1]+dy
            if not in_bounds(neighbor,width,height) or neighbor in blocked:
                continue
            charged = cell if reverse else neighbor
            extra = 1 + (damage if charged in hazards and charged not in food else 0)
            updated = cost + extra
            if updated < costs.get(neighbor,float("inf")):
                costs[neighbor] = updated
                heappush(queue,(updated,neighbor))
    return costs


def royale_score(game_state, position, blocked, distances):
    if not is_royale(game_state):
        return 0.0
    immediate = hazard_cost(game_state,position)
    if immediate <= -HEAD_DANGER_PENALTY:
        return immediate
    remaining = health_after_step(game_state,position)
    hazards = hazard_cells(game_state)
    costs = health_cost_distances(game_state,position,blocked)
    safe = {cell for cell,cost in costs.items() if cell not in hazards and cost < remaining}
    accessible_food = any(cell in costs and costs[cell] <= remaining for cell in get_food_positions(game_state))
    access_bonus = 25.0 * len(safe) / max(1,game_state["board"]["width"] * game_state["board"]["height"])
    if not safe and not accessible_food:
        return immediate - 1500.0
    # Reward reachable safe space, with no geometric-center preference.
    return immediate + access_bonus


def compute_territory_map(game_state, blocked=None, our_start=None):
    """Repeated BFS Voronoi; equal arrivals remain contested, even if longer."""
    board, you = game_state["board"], game_state["you"]
    blocked = set(get_occupied_cells(game_state) if blocked is None else blocked)
    width, height = board["width"], board["height"]
    starts = [(snake["id"], to_pos(snake["body"][0])) for snake in board["snakes"]]
    maps = []
    for identity, head in starts:
        origin = our_start if identity == you["id"] and our_start is not None else head
        offset = 1 if identity == you["id"] and our_start is not None else 0
        distances = bfs_distances(origin, blocked - {origin}, width, height)
        maps.append((identity, distances, offset))
    ours, enemies, contested = set(), set(), set()
    ownership = {}
    for x in range(width):
        for y in range(height):
            cell = (x, y)
            if cell in blocked:
                continue
            arrivals = [(distances[cell] + offset, identity) for identity, distances, offset in maps if cell in distances]
            if not arrivals:
                continue
            first = min(distance for distance, _ in arrivals)
            winners = [identity for distance, identity in arrivals if distance == first]
            owner = winners[0] if len(winners) == 1 else None
            ownership[cell] = owner
            if owner is None:
                contested.add(cell)
            elif owner == you["id"]:
                ours.add(cell)
            else:
                enemies.add(cell)
    free_cells = max(1, width * height - len({p for p in blocked if in_bounds(p,width,height)}))
    return {"ownership": ownership, "our_territory": ours, "enemy_territory": enemies,
            "contested_cells": contested, "territory_ratio": len(ours) / free_cells}


def get_strategy_profile(game_state):
    alive = len(game_state["board"]["snakes"])
    # Bounded rewards retain the same survival hierarchy at every player count.
    pressure = 0.15 if alive >= 4 else 0.45 if alive == 3 else 1.0 if alive == 2 else 0.0
    return {
        "space_weight": 1.2 if alive >= 4 else 1.1 if alive == 3 else 1.0,
        "food_weight": 0.8 if alive >= 4 else 0.9 if alive == 3 else 1.0,
        "aggression_weight": pressure,
        "territory_weight": 15.0 if alive >= 4 else 30.0 if alive == 3 else 60.0 if alive == 2 else 0.0,
        "head_pressure_weight": 12.0 * pressure,
        "hazard_weight": 1.0,
    }


def get_food_positions(game_state):
    return {to_pos(cell) for cell in game_state["board"].get("food", [])}


def bfs_distances(start, blocked, width, height):
    """Static hard-occupancy distances; a blocked source is unreachable."""
    if start in blocked or not in_bounds(start, width, height):
        return {}
    distances = {start: 0}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for dx, dy in DIRECTIONS.values():
            cell = x + dx, y + dy
            if in_bounds(cell, width, height) and cell not in blocked and cell not in distances:
                distances[cell] = distances[(x, y)] + 1
                queue.append(cell)
    return distances


def nearest_reachable_food_distance(distances, food):
    return min((distances[pos] for pos in food if pos in distances), default=None)


def get_dynamic_food_weight(health):
    if health > 70:
        return 4.0
    if health > 40:
        return 30.0
    if health > 20:
        return 90.0
    return 240.0


def build_food_attraction(game_state, blocked=None, danger=None, deadline=None):
    """BFS food field, excluding dangerous paths and discounting enemy races.

    Max rather than sum keeps many foods from overwhelming survival penalties.
    The current head stays blocked: paths cannot reverse through our new neck.
    """
    board, you = game_state["board"], game_state["you"]
    width, height = board["width"], board["height"]
    blocked = set(get_occupied_cells(game_state) if blocked is None else blocked)
    danger = build_head_danger_map(game_state) if danger is None else danger
    length = len(you["body"])
    unsafe = {pos for pos, size in danger.items() if size >= length}
    enemies = []
    for enemy in board["snakes"]:
        if enemy["id"] != you["id"] and len(enemy["body"]) >= length:
            head = to_pos(enemy["body"][0])
            enemies.append(bfs_distances(head, blocked - {head}, width, height))
    attraction = {}
    urgency = get_dynamic_food_weight(you.get("health", 100))
    hazards = hazard_cells(game_state)
    damage = hazard_damage(game_state)
    head = to_pos(you["body"][0])
    from_head = bfs_distances(head, (blocked | unsafe) - {head}, width, height)
    # Bound pathological food-dense boards. Rank by reachable distance, not geometry.
    targets = sorted((food for food in get_food_positions(game_state) if food in from_head),
                     key=lambda food: (from_head[food], food))[:FOOD_TARGET_LIMIT]
    for food in targets:
        if deadline is not None and perf_counter() >= deadline:
            break
        distances = bfs_distances(food, blocked | unsafe, width, height)
        if len(distances) < length + 1:
            continue
        # An isolated pocket or cul-de-sac is poor food even when close.
        quality = min(1.0, len(distances) / (SPACE_RATIO_THRESHOLD * (length + 1)))
        if count_safe_exits(food, blocked, width, height) < 2:
            quality *= 0.1
        enemy_distance = min((d.get(food, float("inf")) for d in enemies), default=float("inf"))
        energy = health_cost_distances(game_state, food, blocked | unsafe, reverse=True) if is_royale(game_state) else distances
        for cell, distance in distances.items():
            steps = distance + 1
            entry_cost = 1 + (damage if cell in hazards and cell != food else 0)
            if energy.get(cell, float("inf")) + entry_cost > you.get("health", 100):
                continue
            if steps > you.get("health", 100):
                continue
            contest = 0.1 if enemy_distance <= steps else 1.0
            value = urgency * quality * contest / steps
            attraction[cell] = max(attraction.get(cell, 0.0), value)
    return attraction


def food_score_for_move(game_state, move, attraction=None):
    if attraction is None:
        attraction = build_food_attraction(game_state)
    return attraction.get(next_position(to_pos(game_state["you"]["body"][0]), move), 0.0)


def score_move_components(game_state, move, blocked=None, strategic_weights=None):
    head = to_pos(game_state["you"]["body"][0])
    destination = next_position(head, move)
    board = game_state["board"]
    width, height = board["width"], board["height"]
    occupied = get_effective_blocked_cells(game_state, move)
    components = dict.fromkeys(("safety", "space", "exits", "trap", "head", "food",
                                "starvation", "territory", "hazard", "aggression", "search"), 0.0)
    if not in_bounds(destination, width, height) or destination in occupied:
        components["safety"] = -float("inf")
        return components
    blocked = set(occupied if blocked is None else blocked)
    # Respect custom obstacles, but apply candidate tail release to raw occupancy.
    blocked -= get_occupied_cells(game_state) - occupied
    blocked.discard(destination)
    blocked.add(head)
    distances = bfs_distances(destination, blocked, width, height)
    reachable = len(distances)
    length = len(game_state["you"]["body"]) + (destination in get_food_positions(game_state))
    profile = get_strategy_profile(game_state)
    components["space"] = min(reachable, 400) * SPACE_WEIGHT * profile["space_weight"]
    components["exits"] = count_safe_exits(destination, blocked, width, height) * EXIT_WEIGHT
    if reachable < length:
        components["trap"] = -TRAP_PENALTY
    elif reachable / max(1, length) < SPACE_RATIO_THRESHOLD:
        components["trap"] = -TRAP_PENALTY * 0.5
    if strategic_weights is None:
        strategic_weights = build_strategic_weights(game_state)
    danger = build_head_danger_map(game_state)
    if danger.get(destination, 0) >= len(game_state["you"]["body"]):
        components["head"] = -HEAD_DANGER_PENALTY
    attraction = strategic_weights.get(destination, 0.0) - components["head"] - hazard_cost(game_state, destination)
    components["food"] = max(0.0, min(get_dynamic_food_weight(game_state["you"].get("health",100)), attraction)) * profile["food_weight"]
    if components["trap"] == 0 and components["head"] == 0 and profile["territory_weight"]:
        territory = compute_territory_map(game_state, blocked, destination)
        components["territory"] = territory["territory_ratio"] * profile["territory_weight"]
    if components["trap"] == 0 and components["head"] == 0:
        components["aggression"] = aggression_score(game_state,destination,blocked,reachable,profile)
    components["hazard"] = royale_score(game_state, destination, blocked, distances) * profile["hazard_weight"]
    health = game_state["you"].get("health", 100)
    food = get_food_positions(game_state)
    food_distances = health_cost_distances(game_state,destination,blocked) if is_royale(game_state) and health <= 20 else distances
    distance = nearest_reachable_food_distance(food_distances,food)
    entry_cost = 1 + (hazard_damage(game_state) if destination in hazard_cells(game_state) and destination not in food else 0)
    if health_after_step(game_state, destination) <= 0:
        components["starvation"] = -HEAD_DANGER_PENALTY
    elif health <= 20 and destination not in food and (distance is None or distance + entry_cost > health):
        components["starvation"] = -1500.0
    return components


def evaluate_move(game_state, move, blocked=None, strategic_weights=None):
    return sum(score_move_components(game_state, move, blocked, strategic_weights).values())


# info is called when you create your Battlesnake on play.battlesnake.com
# and controls your Battlesnake's appearance
# TIP: If you open your Battlesnake URL in a browser you should see this data
def info() -> typing.Dict:
    print("INFO")

    return {
        "apiversion": "1",
        "author": "",  # TODO: Your Battlesnake Username
        "color": "#888888",  # TODO: Choose color
        "head": "default",  # TODO: Choose head
        "tail": "default",  # TODO: Choose tail
    }


# start is called when your Battlesnake begins a game
def start(game_state: typing.Dict):
    print("GAME START")


def death_reason(game_state):
    """Use explicit elimination evidence when supplied; ordinary /end may lack it."""
    you = game_state.get("you", {})
    cause = you.get("elimination_event", {}).get("cause", you.get("eliminatedCause", ""))
    known = {"wall-collision":"WALL", "snake-collision":"BODY", "snake-self-collision":"BODY",
             "head-collision":"HEAD_TO_HEAD", "out-of-health":"STARVATION", "hazard":"HAZARD",
             "timeout":"TIMEOUT", "trapped":"TRAPPED"}
    if cause in known:
        return known[cause]
    body = you.get("body", [])
    if body:
        head = to_pos(body[0])
        board = game_state["board"]
        if not in_bounds(head,board["width"],board["height"]):
            return "WALL"
        if you.get("health",100) <= 0:
            return "HAZARD" if head in hazard_cells(game_state) else "STARVATION"
    return "UNKNOWN"


def end(game_state: typing.Dict):
    alive = any(snake["id"] == game_state["you"]["id"] for snake in game_state["board"]["snakes"])
    print(json.dumps({"event":"end", "turn":game_state.get("turn"),
                      "game_id":game_state.get("game",{}).get("id"), "snake_id":game_state["you"]["id"],
                      "outcome":"survived" if alive else "eliminated",
                      "death_reason":None if alive else death_reason(game_state)},separators=(",",":")))


def log_decision(game_state, chosen, started, components, timed_out=False, fallback=False):
    if os.environ.get("BATTLESNAKE_LOG", "1") == "0":
        return
    print(json.dumps({"event":"move", "turn":game_state.get("turn"),
                      "game_id":game_state.get("game",{}).get("id"), "snake_id":game_state["you"]["id"],
                      "decision_time_ms":round((perf_counter()-started)*1000,2),
                      "chosen_move":chosen, "scores":{key:round(value,2) for key,value in components.items()},
                      "snakes_alive":len(game_state["board"]["snakes"]),
                      "health":game_state["you"].get("health",100),
                      "ruleset":game_state.get("game",{}).get("ruleset",{}).get("name","standard"),
                      "search_timeout":timed_out,"fallback":fallback,
                      "search_depth":components.get("search_depth", 0),
                      "search_nodes":components.get("search_nodes", 0)},separators=(",",":")))


def move(game_state: typing.Dict, search_enabled=None) -> typing.Dict:
    started = perf_counter()
    if search_enabled is None:
        search_enabled = os.environ.get("BATTLESNAKE_SEARCH", "1") != "0"
    timeout = game_state.get("game",{}).get("timeout",500) / 1000
    deadline = started + min(HARD_CUTOFF_SECONDS, max(0.001,timeout * 0.6))
    safe_moves = get_safe_moves(game_state, tail_aware=True)
    if not safe_moves:
        log_decision(game_state,"down",started,{},fallback=True)
        return {"move":"down"}

    blocked = get_occupied_cells(game_state)
    strategic_weights = build_strategic_weights(game_state,deadline=deadline)
    components = {}
    for direction in safe_moves:
        if components and perf_counter() >= deadline:
            break
        components[direction] = score_move_components(game_state,direction,blocked,strategic_weights)
    scores = {direction:sum(parts.values()) for direction,parts in components.items()}
    chosen = max(scores,key=lambda direction:(scores[direction],-MOVE_PRIORITY.index(direction)))
    heuristic_choice = chosen
    immediate_penalties = {}
    if search_enabled and len(select_relevant_snakes(game_state)) > 1:
        legacy_deadline = min(deadline, perf_counter() + 0.03)
        legacy_choice, immediate_penalties, legacy_timeout = choose_move(
            game_state, scores, chosen, legacy_deadline, enabled=True
        )
        if not legacy_timeout and legacy_choice in scores:
            heuristic_choice = legacy_choice
            chosen = legacy_choice
    search_deadline = min(deadline,perf_counter()+SEARCH_BUDGET_SECONDS)
    deep_result = iterative_deepening_search(
        game_state,
        chosen,
        search_deadline,
        enabled=search_enabled,
        max_depth=max(1, int(os.environ.get("BATTLESNAKE_MAX_DEPTH", "2"))),
    )
    if (
        deep_result.completed_depth > 0
        and deep_result.move in scores
        # A tree value cannot override immediate hard-safety and trap gates.
        and components[deep_result.move].get("trap", 0.0) >= 0.0
        and components[deep_result.move].get("head", 0.0) == 0.0
        and components[deep_result.move].get("starvation", 0.0) > -10000.0
    ):
        chosen = deep_result.move
        # Preserve the established one-turn safety gate when MaxN proposes a
        # different move. A deeper positional vector must not reintroduce a
        # response that the validated immediate search marks as fatal.
        if deep_result.algorithm == "maxn" and chosen != heuristic_choice:
            if not immediate_penalties:
                safety_deadline = min(deadline, perf_counter() + 0.02)
                _, immediate_penalties, _ = choose_move(
                    game_state, {chosen: scores[chosen]}, chosen,
                    safety_deadline, enabled=True
                )
            if immediate_penalties.get(chosen, 0.0) <= -20000.0:
                chosen = heuristic_choice
    timed_out = deep_result.timed_out
    search_scores = {chosen: deep_result.score - scores.get(chosen, 0.0)}
    components[chosen]["search"] = search_scores[chosen]
    components[chosen]["search_depth"] = float(deep_result.completed_depth)
    components[chosen]["search_nodes"] = float(deep_result.nodes)
    log_decision(game_state,chosen,started,components[chosen],timed_out)
    return {"move":chosen}


# Start server when `python main.py` is run
if __name__ == "__main__":
    from server import run_server

    run_server({"info": info, "start": start, "move": move, "end": end})
