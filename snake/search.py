"""Bounded one-turn maximin with a next-exit check; no deep multiplayer tree."""
from copy import deepcopy
from itertools import product
from time import perf_counter

SEARCH_BUDGET_SECONDS = 0.22
HARD_CUTOFF_SECONDS = 0.27
SEARCH_DEATH_PENALTY = 20000.0


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
        space = bot.flood_fill_space(position,blocked,state['board']['width'],state['board']['height'])
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
    options = [plausible_responses(state,enemy) for enemy in enemies]
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
