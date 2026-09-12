import copy
import pytest
import main
from tests.fixtures import make_state, make_snake


def test_food_extraction_and_bfs_wall():
    state = make_state(food=[{'x': 2, 'y': 1}])
    assert main.get_food_positions(state) == {(2, 1)}
    distances = main.bfs_distances((0, 1), {(1, y) for y in range(3)}, 3, 3)
    assert main.nearest_reachable_food_distance(distances, {(2, 1)}) is None
    assert main.bfs_distances((0, 0), {(0, 0)}, 3, 3) == {}


@pytest.mark.parametrize('health,weight', [(100,4),(71,4),(70,30),(41,30),(40,90),(21,90),(20,240),(1,240)])
def test_health_bands(health, weight):
    assert main.get_dynamic_food_weight(health) == weight


@pytest.mark.parametrize('health', [55, 30, 2])
def test_food_changes_choice(health):
    state = make_state(you=make_snake(health=health), food=[{'x':6,'y':5}])
    assert main.move(state)['move'] == 'right'


def test_food_component_bounded_and_no_food_zero():
    state = make_state(food=[{'x':6,'y':5}])
    assert 0 < main.score_move_components(state, 'right')['food'] <= 4
    assert main.score_move_components(make_state(), 'up')['food'] == 0


def test_bfs_detour_not_manhattan():
    distances = main.bfs_distances((0,0), {(1,0),(1,1)}, 3,3)
    assert distances[(2,0)] == 6


def test_contested_food_and_safer_alternative():
    enemy = make_snake('enemy', body=[{'x':7,'y':5},{'x':7,'y':4},{'x':7,'y':3}])
    state = make_state(you=make_snake(health=10), enemies=[enemy], food=[{'x':6,'y':5},{'x':5,'y':7}])
    assert main.food_score_for_move(state, 'right') == 0
    assert main.move(state)['move'] == 'up'


def test_shorter_contest_stays_viable():
    enemy = make_snake('enemy', body=[{'x':7,'y':5},{'x':7,'y':4}])
    state = make_state(enemies=[enemy], food=[{'x':6,'y':5}])
    assert main.food_score_for_move(state, 'right') > 0


def test_food_trap_does_not_overcome_survival():
    enemy = make_snake('wall', body=[{'x':7,'y':5},{'x':6,'y':6},{'x':6,'y':4}])
    state = make_state(you=make_snake(health=10), enemies=[enemy], food=[{'x':6,'y':5},{'x':4,'y':5}])
    assert main.score_move_components(state,'right')['trap'] < 0
    assert main.move(state)['move'] == 'left'


def test_determinism_and_inputs_unchanged():
    state = make_state(food=[{'x':6,'y':5}])
    original = copy.deepcopy(state)
    blocked = main.get_occupied_cells(state)
    before = blocked.copy()
    assert main.evaluate_move(state,'up',blocked) == main.evaluate_move(state,'up',blocked)
    assert state == original and blocked == before


def test_immediate_food_prevents_starvation():
    state = make_state(you=make_snake(health=1), food=[{'x':6,'y':5}])
    assert main.score_move_components(state, 'right')['starvation'] == 0
    assert main.score_move_components(state, 'up')['starvation'] < 0
    assert main.evaluate_move(state,'down') == -float('inf')
