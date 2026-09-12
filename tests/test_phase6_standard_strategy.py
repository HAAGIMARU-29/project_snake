import main
import pytest
from tests.fixtures import make_state, make_snake


def population(n):
    return make_state(enemies=[make_snake(str(i),body=[{'x':i,'y':0}]) for i in range(n-1)])


def test_pressure_rises_as_population_falls():
    four, three, two = [main.get_strategy_profile(population(n)) for n in (4,3,2)]
    for key in ('aggression_weight','head_pressure_weight','territory_weight'):
        assert four[key] < three[key] < two[key]
    assert four['space_weight'] > three['space_weight'] >= two['space_weight']


@pytest.mark.parametrize('n',[1,2,3,4])
def test_profile_deterministic_and_hard_collision_rejected(n):
    state = population(n)
    assert main.get_strategy_profile(state) == main.get_strategy_profile(state)
    assert main.evaluate_move(state,'down') == -float('inf')


def test_alive_count_changes_score():
    assert main.score_move_components(population(4),'up')['space'] > main.score_move_components(population(2),'up')['space']


def test_head_penalty_independent_of_aggression():
    for n in [2,3,4]:
        state = population(n)
        state['board']['snakes'][1] = make_snake('danger',body=[{'x':7,'y':5},{'x':7,'y':4},{'x':7,'y':3}])
        assert main.score_move_components(state,'right')['head'] == -main.HEAD_DANGER_PENALTY
        assert main.move(state)['move'] != 'right'
