import copy
import pytest
import main
from tests.fixtures import make_state, make_snake


def symmetric(size=11):
    return make_state(width=size,height=size,you=make_snake(body=[{'x':1,'y':size//2}]),enemies=[make_snake('enemy',body=[{'x':size-2,'y':size//2}])])


@pytest.mark.parametrize('size',[11,19])
def test_symmetric_ownership_normalized(size):
    result = main.compute_territory_map(symmetric(size))
    assert len(result['our_territory']) == len(result['enemy_territory'])
    assert len(result['contested_cells']) == size
    assert 0.4 < result['territory_ratio'] < 0.5
    assert (0,0) in result['our_territory']
    assert (size-1,0) in result['enemy_territory']


def test_body_wall_and_disconnected_regions():
    state = symmetric()
    blocked = main.get_occupied_cells(state) | {(5,y) for y in range(11)}
    result = main.compute_territory_map(state,blocked)
    assert not result['contested_cells']
    assert all(x < 5 for x,y in result['our_territory'])
    assert all(x > 5 for x,y in result['enemy_territory'])


def test_multi_enemy_deterministic_no_mutation():
    state = symmetric()
    state['board']['snakes'].append(make_snake('third',body=[{'x':5,'y':9}]))
    original = copy.deepcopy(state)
    blocked = main.get_occupied_cells(state)
    saved = blocked.copy()
    assert main.compute_territory_map(state,blocked) == main.compute_territory_map(state,blocked)
    assert state == original and blocked == saved


def test_territory_never_rewards_trap():
    state = make_state(enemies=[make_snake('wall',body=[{'x':7,'y':5},{'x':6,'y':6},{'x':6,'y':4}])])
    components = main.score_move_components(state,'right')
    assert components['trap'] < 0
    assert components['territory'] == 0


def test_unreachable_cells_have_no_owner():
    state = symmetric()
    blocked = {(x,4) for x in range(11)} | {(x,6) for x in range(11)}
    result = main.compute_territory_map(state,blocked)
    assert (0,0) not in result['ownership']
