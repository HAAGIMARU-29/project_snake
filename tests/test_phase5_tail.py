import copy
import main
from tests.fixtures import make_state, make_snake


def loop(food=None):
    return make_state(you=make_snake(body=[{'x':5,'y':5},{'x':5,'y':4},{'x':4,'y':4},{'x':4,'y':5}]), food=food)


def test_own_tail_release_and_legacy_safety():
    state = loop()
    assert (4,5) not in main.get_effective_blocked_cells(state,'left')
    assert 'left' in main.get_safe_moves(state, tail_aware=True)
    assert 'left' not in main.get_safe_moves(state)
    assert main.evaluate_move(state,'left') > 0


def test_eating_retains_tail():
    state = loop([{'x':4,'y':5}])
    assert (4,5) in main.get_effective_blocked_cells(state,'left')
    assert 'left' not in main.get_safe_moves(state, tail_aware=True)


def test_growth_elsewhere_keeps_tail():
    assert (4,5) in main.get_effective_blocked_cells(loop([{'x':5,'y':6}]),'up')


def test_stacked_tail_stays_blocked():
    state = loop()
    state['you']['body'].append({'x':4,'y':5})
    assert 'left' not in main.get_safe_moves(state, tail_aware=True)


def test_enemy_tail_conservative_with_or_without_food():
    for food in [[], [{'x':7,'y':6}]]:
        enemy = make_snake('enemy', body=[{'x':7,'y':5},{'x':7,'y':4},{'x':6,'y':4},{'x':6,'y':5}])
        state = make_state(enemies=[enemy],food=food)
        assert 'right' not in main.get_safe_moves(state,tail_aware=True)


def test_middle_body_never_opens():
    state = loop()
    assert (5,4) in main.get_effective_blocked_cells(state,'down')
    assert main.evaluate_move(state,'down') == -float('inf')


def test_tail_only_escape():
    state = loop()
    state['board']['snakes'].append(make_snake('wall',body=[{'x':5,'y':6},{'x':6,'y':5}]))
    assert main.move(state)['move'] == 'left'


def test_occupancy_and_bodies_not_mutated():
    state = loop()
    original = copy.deepcopy(state)
    blocked = main.get_occupied_cells(state)
    saved = blocked.copy()
    main.get_effective_blocked_cells(state,'left')
    assert main.evaluate_move(state,'left',blocked) == main.evaluate_move(state,'left')
    assert blocked == saved and state == original
