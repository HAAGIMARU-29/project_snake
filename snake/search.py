"""Bounded tactical search and the foundation for iterative game-tree search."""
from copy import deepcopy
from dataclasses import dataclass
from itertools import product
from time import perf_counter

SEARCH_BUDGET_SECONDS = 0.22
HARD_CUTOFF_SECONDS = 0.27
SEARCH_DEATH_PENALTY = 20000.0
RELEVANT_ENEMY_DISTANCE = 4
MAX_ORDERED_ACTIONS = 3
MAX_MAXN_ACTIONS = 2
MAX_MAXN_DEPTH = 1


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
    vector: tuple = ()


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
    space = bot.flood_fill_space(head, blocked, state["board"]["width"], state["board"]["height"], limit=200)
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


class _SearchTimeout(Exception):
    """Internal control flow used to discard an incomplete depth."""


def _ordered_moves(state, snake_id, root_id=None):
    """Order legal moves with a cheap tactical score, then stable priority.

    Calling the full strategic evaluator at every tree node defeats the point of
    move ordering. The complete scorer still evaluates the root candidates.
    """
    import main as bot

    moves = generate_search_moves(state, snake_id)
    if not moves:
        return ["up"]
    view = _snake_view(state, snake_id)
    scored = []
    head = bot.to_pos(view["you"]["body"][0])
    food = bot.get_food_positions(view)
    danger = bot.build_head_danger_map(view)
    body_length = len(view["you"]["body"])
    for move in moves:
        destination = bot.next_position(head, move)
        score = 0.0
        if destination in food:
            score += 100.0
        if danger.get(destination, 0) >= body_length:
            score -= 10000.0
        score += bot.count_safe_exits(
            destination,
            bot.get_effective_blocked_cells(view, move),
            view["board"]["width"],
            view["board"]["height"],
        ) * bot.EXIT_WEIGHT
        scored.append((move, score))
    ordered = [move for move, _ in sorted(
        scored,
        key=lambda item: (-item[1], bot.MOVE_PRIORITY.index(item[0])),
    )]
    # Branch bounding is applied only to internal action ordering. The caller's
    # heuristic fallback remains available when a search result is incomplete.
    limit = MAX_MAXN_ACTIONS if len(state["board"].get("snakes", [])) > 2 else MAX_ORDERED_ACTIONS
    return ordered[:limit]


def _root_alive(state, root_id):
    return any(snake.get("id") == root_id and snake.get("body")
               for snake in state.get("board", {}).get("snakes", []))


def _joint_turn(state, root_id, root_move, opponents, opponent_moves):
    moves = {root_id: root_move}
    moves.update({snake_id: move for snake_id, move in zip(opponents, opponent_moves)})
    return simulate_turn(state, moves)


def _alpha_beta_node(state, root_id, opponent_id, depth, alpha, beta,
                     deadline, table, stats, clock):
    if deadline_expired(deadline, clock):
        raise _SearchTimeout
    stats["nodes"] += 1
    if depth <= 0 or not _root_alive(state, root_id):
        return evaluate_search_state(state, root_id, [root_id, opponent_id])
    key = (fingerprint_state(state, root_id), opponent_id, depth)
    cached = table.get(key)
    if cached is not None:
        stats["cache_hits"] += 1
        return cached

    root_moves = _ordered_moves(state, root_id, root_id)
    opponent_moves = _ordered_moves(state, opponent_id, root_id)
    best = -float("inf")
    for root_move in root_moves:
        worst = float("inf")
        for opponent_move in opponent_moves:
            if deadline_expired(deadline, clock):
                raise _SearchTimeout
            future, reasons = _joint_turn(
                state, root_id, root_move, [opponent_id], [opponent_move]
            )
            value = (-SEARCH_DEATH_PENALTY if root_id in reasons else
                     _alpha_beta_node(future, root_id, opponent_id, depth - 1,
                                      alpha, beta, deadline, table, stats, clock))
            worst = min(worst, value)
            beta = min(beta, worst)
            if beta <= alpha:
                break
        best = max(best, worst)
        alpha = max(alpha, best)
        if beta <= alpha:
            break
    table[key] = best
    return best


def alpha_beta_root(state, root_id, opponent_id, depth, deadline,
                    table=None, clock=perf_counter):
    """Search one complete turn per depth in a two-player Alpha-Beta tree."""
    table = {} if table is None else table
    stats = {"nodes": 0, "cache_hits": 0}
    root_moves = _ordered_moves(state, root_id, root_id)
    opponent_moves = _ordered_moves(state, opponent_id, root_id)
    if not root_moves:
        return SearchResult("down", -SEARCH_DEATH_PENALTY, depth,
                            stats["nodes"], stats["cache_hits"], False, "alphabeta")
    best_move = root_moves[0]
    best = -float("inf")
    alpha = -float("inf")
    for root_move in root_moves:
        if deadline_expired(deadline, clock):
            raise _SearchTimeout
        worst = float("inf")
        for opponent_move in opponent_moves:
            if deadline_expired(deadline, clock):
                raise _SearchTimeout
            future, reasons = _joint_turn(
                state, root_id, root_move, [opponent_id], [opponent_move]
            )
            value = (-SEARCH_DEATH_PENALTY if root_id in reasons else
                     _alpha_beta_node(future, root_id, opponent_id, depth - 1,
                                      alpha, float("inf"), deadline, table,
                                      stats, clock))
            worst = min(worst, value)
            if worst <= alpha:
                break
        if worst > best:
            best, best_move = worst, root_move
        alpha = max(alpha, best)
    return SearchResult(best_move, best, depth, stats["nodes"],
                        stats["cache_hits"], False, "alphabeta")


def _player_utility(state, player_id, player_ids):
    value = evaluate_search_state(state, player_id, player_ids)
    # Keep a cheap root safety gate inside MaxN's utility. The full one-turn
    # response search is reserved for the existing live safety gate; repeating
    # it at every MaxN leaf would consume the entire board-time budget.
    if player_ids and player_id == player_ids[0]:
        choices = generate_search_moves(state, player_id)
        if not choices:
            value -= SEARCH_DEATH_PENALTY
        else:
            import main as bot
            length = len(state["you"]["body"])
            danger = bot.build_head_danger_map(state)
            if all(danger.get(bot.next_position(bot.to_pos(state["you"]["body"][0]), move), 0) >= length
                   for move in choices):
                value -= SEARCH_DEATH_PENALTY
    return value


def _maxn_node(state, player_ids, depth, actor_index, pending,
               deadline, table, stats, clock):
    if deadline_expired(deadline, clock):
        raise _SearchTimeout
    stats["nodes"] += 1
    if depth <= 0:
        return tuple(_player_utility(state, player_id, player_ids)
                     for player_id in player_ids)
    key = (fingerprint_state(state, player_ids[0]), depth, actor_index,
           tuple(sorted(pending.items())))
    cached = table.get(key)
    if cached is not None:
        stats["cache_hits"] += 1
        return cached

    actor_id = player_ids[actor_index]
    moves = _ordered_moves(state, actor_id, player_ids[0])
    best_vector = None
    for move in moves:
        if deadline_expired(deadline, clock):
            raise _SearchTimeout
        next_pending = dict(pending)
        next_pending[actor_id] = move
        if actor_index + 1 < len(player_ids):
            vector = _maxn_node(state, player_ids, depth, actor_index + 1,
                                next_pending, deadline, table, stats, clock)
        else:
            all_moves = dict(next_pending)
            for snake in state["board"].get("snakes", []):
                snake_id = snake.get("id")
                if snake_id in all_moves:
                    continue
                fallback_moves = _ordered_moves(state, snake_id, player_ids[0])
                all_moves[snake_id] = fallback_moves[0] if fallback_moves else "up"
            future, reasons = simulate_turn(state, all_moves)
            if player_ids[0] in reasons:
                vector = (-SEARCH_DEATH_PENALTY,) + tuple(
                    _player_utility(future, player_id, player_ids[1:])
                    for player_id in player_ids[1:]
                )
            else:
                vector = _maxn_node(future, player_ids, depth - 1, 0, {},
                                    deadline, table, stats, clock)
        if best_vector is None or vector[actor_index] > best_vector[actor_index]:
            best_vector = vector
    if best_vector is None:
        best_vector = tuple(-SEARCH_DEATH_PENALTY for _ in player_ids)
    table[key] = best_vector
    return best_vector


def maxn_root(state, player_ids, depth, deadline, table=None, clock=perf_counter):
    """Search a multi-snake tree and maximize the acting player's vector entry."""
    table = {} if table is None else table
    stats = {"nodes": 0, "cache_hits": 0}
    root_id = player_ids[0]
    moves = _ordered_moves(state, root_id, root_id)
    best_move = moves[0] if moves else "down"
    best_vector = None
    for move in moves or ["down"]:
        if deadline_expired(deadline, clock):
            raise _SearchTimeout
        vector = _maxn_node(state, list(player_ids), depth, 1, {root_id: move},
                            deadline, table, stats, clock)
        if best_vector is None or vector[0] > best_vector[0]:
            best_vector, best_move = vector, move
    return SearchResult(best_move, best_vector[0] if best_vector else -SEARCH_DEATH_PENALTY,
                        depth, stats["nodes"], stats["cache_hits"], False,
                        "maxn", tuple(best_vector or ()))


def iterative_deepening_search(state, fallback, deadline, enabled=True,
                               max_depth=4, clock=perf_counter):
    """Return only the best move from the last fully completed depth."""
    if not enabled or deadline_expired(deadline, clock):
        return SearchResult(fallback, 0.0, 0, 0, 0,
                            deadline_expired(deadline, clock), "fallback")
    relevant = select_relevant_snakes(state)
    if not relevant:
        return SearchResult(fallback, 0.0, 0, 0, 0, False, "fallback")
    root_id = state["you"]["id"]
    opponent_ids = [snake["id"] for snake in relevant]
    if len(opponent_ids) > 1:
        max_depth = min(int(max_depth), MAX_MAXN_DEPTH)
    last = SearchResult(fallback, 0.0, 0, 0, 0, False, "fallback")
    for depth in range(1, max(1, int(max_depth)) + 1):
        try:
            if len(opponent_ids) == 1:
                result = alpha_beta_root(state, root_id, opponent_ids[0],
                                         depth, deadline, clock=clock)
            else:
                result = maxn_root(state, [root_id] + opponent_ids, depth,
                                   deadline, clock=clock)
        except _SearchTimeout:
            return SearchResult(last.move, last.score, last.completed_depth,
                                last.nodes, last.cache_hits, True,
                                last.algorithm, last.vector)
        last = result
    return last
