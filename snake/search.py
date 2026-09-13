"""Bounded tactical search and the foundation for iterative game-tree search."""
from copy import deepcopy
from dataclasses import dataclass
from itertools import product
from time import perf_counter

SEARCH_BUDGET_SECONDS = 0.22
HARD_CUTOFF_SECONDS = 0.27
SEARCH_DEATH_PENALTY = 20000.0
RELEVANT_ENEMY_DISTANCE = 4


@dataclass(frozen=True)
class SearchResult:
    """Completed search information safe to return across the module boundary."""

    move: str
    score: float
    completed_depth: int = 0
    nodes: int = 0
    cache_hits: int = 0
    timed_out: bool = False
    algorithm: str = "fallback"


def deadline_expired(deadline, clock=perf_counter):
    """Return true once the monotonic search deadline has been reached."""
    return deadline is not None and clock() >= deadline


def select_relevant_snakes(state, max_distance=RELEVANT_ENEMY_DISTANCE, horizon=2):
    """Select opponents whose bodies can enter our tactical neighborhood soon.

    Distance is measured from our current head to the nearest enemy body segment,
    rather than just to the enemy head. The horizon multiplier is deliberately
    conservative: a snake farther away than this bound is left to leaf
    approximation in the future MaxN implementation.
    """
    board = state["board"]
    our_id = state["you"]["id"]
    our_head = tuple((state["you"]["body"][0][key] for key in ("x", "y")))
    threshold = max(0, int(max_distance)) * max(1, int(horizon))
    ranked = []
    for index, snake in enumerate(board.get("snakes", [])):
        if snake.get("id") == our_id or not snake.get("body"):
            continue
        nearest = min(
            abs(our_head[0] - segment["x"]) + abs(our_head[1] - segment["y"])
            for segment in snake["body"]
        )
        if nearest <= threshold:
            ranked.append((nearest, snake.get("id", ""), index, snake))
    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    return [snake for _, _, _, snake in ranked]


def _snake_view(state, snake_id):
    """Create a shallow perspective view without modifying the request state."""
    for snake in state["board"].get("snakes", []):
        if snake.get("id") == snake_id:
            view = dict(state)
            view["you"] = snake
            view["board"] = dict(state["board"])
            view["board"]["snakes"] = list(state["board"].get("snakes", []))
            return view
    return None


def generate_search_moves(state, snake_id):
    """Return deterministic hard-safe directions for any snake perspective."""
    import main as bot

    view = _snake_view(state, snake_id)
    if view is None:
        return []
    return bot.get_safe_moves(view, tail_aware=True)


def fingerprint_state(state, perspective_id=None):
    """Build a deterministic, hashable key for a search transposition table."""
    game = state.get("game", {})
    ruleset = game.get("ruleset", {})
    settings = ruleset.get("settings", {})
    board = state.get("board", {})

    def cell(value):
        return (value.get("x"), value.get("y"))

    def frozen(value):
        """Canonicalize nested rule settings into hashable deterministic values."""
        if isinstance(value, dict):
            return tuple((key, frozen(item)) for key, item in sorted(value.items()))
        if isinstance(value, (list, tuple)):
            return tuple(frozen(item) for item in value)
        return value

    snakes = []
    for snake in sorted(board.get("snakes", []), key=lambda item: item.get("id", "")):
        snakes.append((
            snake.get("id", ""),
            int(snake.get("health", 100)),
            tuple(cell(segment) for segment in snake.get("body", [])),
        ))
    return (
        int(board.get("width", 0)),
        int(board.get("height", 0)),
        state.get("turn", 0),
        ruleset.get("name", "standard"),
        frozen(settings),
        tuple(sorted(cell(food) for food in board.get("food", []))),
        tuple(sorted(cell(hazard) for hazard in board.get("hazards", []))),
        tuple(snakes),
        perspective_id or state.get("you", {}).get("id", ""),
    )


def evaluate_search_state(state, root_id=None, player_ids=None):
    """Evaluate a leaf from the root perspective without tactical recursion.

    The first version intentionally delegates positional detail to the validated
    component evaluator. Later MaxN work can derive one utility component per
    player from this same contract.
    """
    import main as bot

    root_id = root_id or state.get("you", {}).get("id")
    root = next((snake for snake in state.get("board", {}).get("snakes", [])
                 if snake.get("id") == root_id), None)
    if root is None or not root.get("body"):
        return -SEARCH_DEATH_PENALTY
    view = _snake_view(state, root_id)
    head = bot.to_pos(root["body"][0])
    blocked = bot.get_effective_blocked_cells(view)
    blocked.discard(head)
    space = bot.flood_fill_space(head, blocked, state["board"]["width"], state["board"]["height"], limit=400)
    exits = bot.count_safe_exits(head, blocked, state["board"]["width"], state["board"]["height"])
    health = root.get("health", 100)
    length = len(root["body"])
    value = float(space) + exits * bot.EXIT_WEIGHT + health * 0.25 + length * 2.0
    if player_ids and root_id not in player_ids:
        return -SEARCH_DEATH_PENALTY
    return value


def simulate_turn(state, moves):
    # Import lazily so the starter main module remains the public helper API.
    import main as bot
    result = deepcopy(state)
    board = result['board']
    food = bot.get_food_positions(state)
    eaten = set()
    reasons = {}
    for snake in board['snakes']:
        head = bot.next_position(bot.to_pos(snake['body'][0]), moves.get(snake['id'], 'up'))
        body = [{'x':head[0], 'y':head[1]}] + snake['body'][:-1]
        snake['health'] = bot.health_after_step(state,head,snake.get('health',100))
        if head in food:
            # Engine movement pops the old tail; growth duplicates the new tail.
            body.append(dict(body[-1]))
            eaten.add(head)
        snake.update(body=body, head=body[0], length=len(body))
        if not bot.in_bounds(head,board['width'],board['height']):
            reasons[snake['id']] = 'WALL'
        elif snake['health'] <= 0:
            reasons[snake['id']] = 'HAZARD' if head in bot.hazard_cells(state) else 'STARVATION'
    active = [snake for snake in board['snakes'] if snake['id'] not in reasons]
    for snake in active:
        head = bot.to_pos(snake['body'][0])
        if any(head == bot.to_pos(segment) for other in active for segment in other['body'][1:]):
            reasons[snake['id']] = 'BODY'
        elif any(other['id'] != snake['id'] and other['head'] == snake['head']
                 and len(other['body']) >= len(snake['body']) for other in active):
            reasons[snake['id']] = 'HEAD_TO_HEAD'
    board['snakes'] = [snake for snake in active if snake['id'] not in reasons]
    board['food'] = [cell for cell in board.get('food',[]) if bot.to_pos(cell) not in eaten]
    result['turn'] = state.get('turn',0) + 1
    result['you'] = next((snake for snake in board['snakes'] if snake['id']==state['you']['id']), result['you'])
    return result, reasons


def plausible_responses(state, enemy):
    import main as bot
    view = dict(state, you=enemy)
    choices = bot.get_safe_moves(view,tail_aware=True)
    # Include enemy tails that could release, even though our own legal filter
    # deliberately avoids betting on enemy choices. Overmodeling is conservative.
    head = bot.to_pos(enemy['body'][0])
    possible_blocked = bot.get_occupied_cells(state)
    for snake in state['board']['snakes']:
        tail = bot.to_pos(snake['body'][-1])
        if sum(bot.to_pos(c)==tail for s in state['board']['snakes'] for c in s['body']) == 1:
            possible_blocked.discard(tail)
    for direction in bot.MOVE_PRIORITY:
        position = bot.next_position(head,direction)
        if bot.in_bounds(position,state['board']['width'],state['board']['height']) and position not in possible_blocked and direction not in choices:
            choices.append(direction)
    return choices or ['up']


def response_penalty(state, our_id):
    import main as bot
    if not any(snake['id']==our_id for snake in state['board']['snakes']):
        return -SEARCH_DEATH_PENALTY
    choices = bot.get_safe_moves(state,tail_aware=True)
    danger = bot.build_head_danger_map(state)
    length = len(state['you']['body'])
    head = bot.to_pos(state['you']['body'][0])
    best_space = 0
    for direction in choices:
        position = bot.next_position(head,direction)
        if danger.get(position,0) >= length or bot.health_after_step(state,position) <= 0:
            continue
        blocked = bot.get_effective_blocked_cells(state,direction) - {position}
        space = bot.flood_fill_space(position,blocked,state['board']['width'],state['board']['height'],limit=length)
        if space >= length:
            return 0.0
        best_space = max(best_space,space)
    if best_space == 0:
        return -SEARCH_DEATH_PENALTY
    if best_space < length:
        return -bot.TRAP_PENALTY
    return 0.0


def choose_move(state, scores, fallback, deadline=None, enabled=True, clock=perf_counter):
    """Discard an incomplete search, so deadline fallback has no order bias."""
    import main as bot
    if not enabled or not scores:
        return fallback, {}, False
    deadline = clock()+SEARCH_BUDGET_SECONDS if deadline is None else deadline
    if clock() >= deadline:
        return fallback, {}, True
    our_id = state['you']['id']
    enemies = [snake for snake in state['board']['snakes'] if snake['id'] != our_id]
    head = bot.to_pos(state['you']['body'][0])
    options = []
    for enemy in enemies:
        enemy_head = bot.to_pos(enemy['body'][0])
        choices = plausible_responses(state,enemy)
        # Two simultaneous turns can close at most four grid steps. Far enemies
        # cannot reach our tactical neighborhood within this search horizon.
        distance = abs(head[0]-enemy_head[0])+abs(head[1]-enemy_head[1])
        options.append(choices if distance <= RELEVANT_ENEMY_DISTANCE else choices[:1])
    penalties = {}
    for direction in scores:
        worst = 0.0
        for responses in product(*options):
            if clock() >= deadline:
                return fallback, {}, True
            moves = dict(zip((enemy['id'] for enemy in enemies),responses))
            moves[our_id] = direction
            future, reasons = simulate_turn(state,moves)
            penalty = -SEARCH_DEATH_PENALTY if our_id in reasons else response_penalty(future,our_id)
            worst = min(worst,penalty)
            if worst <= -SEARCH_DEATH_PENALTY:
                break
        penalties[direction] = worst
    if clock() >= deadline:
        return fallback, {}, True
    choice = max(scores,key=lambda direction: (scores[direction]+penalties[direction],-bot.MOVE_PRIORITY.index(direction)))
    return choice, penalties, False
