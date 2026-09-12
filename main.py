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

import typing
from collections import deque


DIRECTIONS = {
    "up": (0, 1),
    "down": (0, -1),
    "left": (-1, 0),
    "right": (1, 0),
}

MOVE_PRIORITY = ["up", "right", "down", "left"]

SPACE_WEIGHT = 1.0
EXIT_WEIGHT = 5.0
TRAP_PENALTY = 1000.0
SPACE_RATIO_THRESHOLD = 1.5

BASE_CELL_WEIGHT = 0.0
HEAD_DANGER_PENALTY = 10000.0
SHORTER_ENEMY_HEAD_BONUS = 0.0


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


def flood_fill_space(start: typing.Tuple[int, int], blocked: typing.Set[typing.Tuple[int, int]], width: int, height: int) -> int:
    if start in blocked or not in_bounds(start, width, height):
        return 0

    visited = set([start])
    queue = deque([start])
    count = 0

    while queue:
        current = queue.popleft()
        count += 1
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

    for snake in game_state.get("board", {}).get("snakes", []):
        if snake.get("id") == our_id:
            continue
        enemy_length = len(snake.get("body", []))
        possible_positions = get_enemy_possible_head_positions(game_state, snake)
        for pos in possible_positions:
            if pos not in danger_map or enemy_length > danger_map[pos]:
                danger_map[pos] = enemy_length
    return danger_map


def build_strategic_weights(game_state: typing.Dict) -> typing.Dict[typing.Tuple[int, int], float]:
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
    for pos, value in build_food_attraction(game_state, danger=danger_map).items():
        weights[pos] += value
    return weights


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


def build_food_attraction(game_state, blocked=None, danger=None):
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
    for food in sorted(get_food_positions(game_state)):
        distances = bfs_distances(food, blocked | unsafe, width, height)
        if len(distances) < length + 1:
            continue
        # An isolated pocket or cul-de-sac is poor food even when close.
        quality = min(1.0, len(distances) / (SPACE_RATIO_THRESHOLD * (length + 1)))
        if count_safe_exits(food, blocked, width, height) < 2:
            quality *= 0.1
        enemy_distance = min((d.get(food, float("inf")) for d in enemies), default=float("inf"))
        for cell, distance in distances.items():
            steps = distance + 1
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
    components["space"] = min(reachable, 400) * SPACE_WEIGHT
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
    components["food"] = strategic_weights.get(destination, 0.0) - components["head"]
    distance = nearest_reachable_food_distance(distances, get_food_positions(game_state))
    health = game_state["you"].get("health", 100)
    if health <= 20 and (distance is None or distance + 1 > health):
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


# end is called when your Battlesnake finishes a game
def end(game_state: typing.Dict):
    print("GAME OVER\n")


# move is called on every turn and returns your next move
# Valid moves are "up", "down", "left", or "right"
# See https://docs.battlesnake.com/api/example-move for available data
def move(game_state: typing.Dict) -> typing.Dict:
    safe_moves = get_safe_moves(game_state, tail_aware=True)

    if not safe_moves:
        chosen_move = "down"
        print(f"MOVE {game_state.get('turn', '?')}: safe=[] chosen={chosen_move} (fallback)")
        return {"move": chosen_move}

    my_head = to_pos(game_state["you"]["body"][0])
    occupied = get_occupied_cells(game_state)
    blocked = set(occupied)
    blocked.discard(my_head)

    strategic_weights = build_strategic_weights(game_state)

    scored_moves = []
    for move in safe_moves:
        new_head = next_position(my_head, move)
        blocked_for_move = set(blocked)
        blocked_for_move.discard(new_head)
        score = evaluate_move(game_state, move, blocked_for_move, strategic_weights)
        scored_moves.append((move, score))

    scored_moves.sort(key=lambda x: (-x[1], MOVE_PRIORITY.index(x[0])))
    chosen_move = scored_moves[0][0]

    score_str = " ".join(f"{m}={s:.1f}" for m, s in scored_moves)
    print(f"MOVE {game_state.get('turn', '?')}: {score_str} | chosen={chosen_move}")
    return {"move": chosen_move}


# Start server when `python main.py` is run
if __name__ == "__main__":
    from server import run_server

    run_server({"info": info, "start": start, "move": move, "end": end})
