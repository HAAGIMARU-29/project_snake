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


def get_safe_moves(game_state: typing.Dict) -> typing.List[str]:
    my_head = to_pos(game_state["you"]["body"][0])
    width = game_state["board"]["width"]
    height = game_state["board"]["height"]
    occupied = get_occupied_cells(game_state)

    safe = []
    for move in MOVE_PRIORITY:
        next_pos = next_position(my_head, move)
        if in_bounds(next_pos, width, height) and next_pos not in occupied:
            safe.append(move)
    return safe


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
    return weights


def evaluate_move(
    game_state: typing.Dict,
    move: str,
    blocked: typing.Optional[typing.Set[typing.Tuple[int, int]]] = None,
    strategic_weights: typing.Optional[typing.Dict[typing.Tuple[int, int], float]] = None,
) -> float:
    my_head = to_pos(game_state["you"]["body"][0])
    new_head = next_position(my_head, move)
    width = game_state["board"]["width"]
    height = game_state["board"]["height"]
    snake_length = len(game_state["you"]["body"])
    blocked = set(get_occupied_cells(game_state) if blocked is None else blocked)
    if strategic_weights is None:
        strategic_weights = build_strategic_weights(game_state)

    reachable = flood_fill_space(new_head, blocked, width, height)
    exits = count_safe_exits(new_head, blocked, width, height)

    score = reachable * SPACE_WEIGHT + exits * EXIT_WEIGHT

    if reachable < snake_length:
        score -= TRAP_PENALTY
    elif reachable / max(1, snake_length) < SPACE_RATIO_THRESHOLD:
        score -= TRAP_PENALTY * 0.5

    score += strategic_weights.get(new_head, 0.0)
    return score


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
    safe_moves = get_safe_moves(game_state)

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
