import pytest
import main
from tests.fixtures import make_state, make_snake


def royale(health=100, size=11, food=None):
    return make_state(width=size,height=size,ruleset='royale',you=make_snake(health=health),hazards=[{'x':6,'y':5}],food=food)


def test_standard_ignores_hazards():
    state = royale()
    state['game']['ruleset']['name']='standard'
    assert main.hazard_cells(state)==set()
    assert main.score_move_components(state,'right')['hazard']==0


def test_health_dependent_hazard_penalty():
    assert -100 < main.hazard_cost(royale(),(6,5)) < 0
    assert main.hazard_cost(royale(20),(6,5)) < main.hazard_cost(royale(),(6,5))
    assert main.hazard_cost(royale(15),(6,5)) == -main.HEAD_DANGER_PENALTY


def test_hazards_are_not_hard_occupancy():
    state = royale()
    assert 'right' in main.get_safe_moves(state,tail_aware=True)
    assert (6,5) not in main.get_effective_blocked_cells(state,'right')
    assert main.build_strategic_weights(state)[(6,5)] < 0


@pytest.mark.parametrize('size',[11,19])
def test_safe_route_and_board_support(size):
    state = royale(size=size)
    assert main.move(state)['move'] != 'right'
    assert main.move(state)==main.move(state)
    assert len(main.build_strategic_weights(state))==size*size


def test_food_in_hazard_resets_health():
    state = royale(1,food=[{'x':6,'y':5}])
    assert main.health_after_step(state,(6,5))==100
    assert main.move(state)['move']=='right'


def test_hazard_only_escape():
    state = royale()
    state['board']['snakes'].append(make_snake('wall',body=[{'x':5,'y':6},{'x':4,'y':5}]))
    assert main.move(state)['move']=='right'


def test_custom_damage_and_energy_routes():
    state = royale(30)
    state['game']['ruleset']['settings']['hazardDamagePerTurn']=40
    assert main.hazard_cost(state,(6,5)) == -main.HEAD_DANGER_PENALTY
    costs = main.health_cost_distances(state,(5,5),set())
    assert costs[(6,5)]==41
    assert costs[(7,5)]==4  # route around the hazard


def test_unaffordable_food_route_has_no_attraction():
    state = royale(20,food=[{'x':8,'y':5}])
    state['board']['hazards']=[{'x':x,'y':y} for x in (6,7) for y in range(11)]
    assert main.food_score_for_move(state,'right') == 0


def test_all_hazards_penalize_no_future_safe_access():
    state = royale()
    state['board']['hazards']=[{'x':x,'y':y} for x in range(11) for y in range(11)]
    assert main.score_move_components(state,'up')['hazard'] < -1000
