import main
from tests.fixtures import make_state, make_snake


def duel(health=100, length=2):
    enemy = make_snake('enemy',body=[{'x':7,'y':5},{'x':7,'y':4},{'x':7,'y':3}][:length])
    return make_state(you=make_snake(health=health),enemies=[enemy])


def test_shorter_pressure_and_food_denial():
    state = duel()
    base = main.score_move_components(state,'right')['aggression']
    assert base > 0
    state['board']['food']=[{'x':6,'y':5}]
    assert main.score_move_components(state,'right')['aggression'] > base


def test_equal_enemy_no_pressure():
    assert main.score_move_components(duel(length=3),'right')['aggression']==0


def test_health_and_own_space_gate():
    state=duel()
    assert main.score_move_components(duel(health=30),'right')['aggression']==0
    assert main.aggression_score(state,(6,5),main.get_occupied_cells(state),2)==0


def test_four_alive_more_conservative():
    state=duel()
    two=main.score_move_components(state,'right')['aggression']
    state['board']['snakes'] += [make_snake(str(x),body=[{'x':x,'y':0}]) for x in (0,2)]
    four=main.score_move_components(state,'right')['aggression']
    assert 0 < four < two


def test_space_reduction_at_chokepoint():
    state=duel()
    blocked=main.get_occupied_cells(state)|{(6,y) for y in range(11) if y!=7}
    pressure=main.aggression_score(state,(6,7),blocked,70)
    open_pressure=main.aggression_score(state,(6,7),main.get_occupied_cells(state),110)
    assert pressure > open_pressure


def test_multi_enemy_danger_cancels_pressure():
    state=duel()
    state['board']['snakes'].append(make_snake('larger',body=[{'x':6,'y':6},{'x':7,'y':6},{'x':8,'y':6},{'x':8,'y':5}]))
    assert main.score_move_components(state,'right')['aggression']==0
    assert main.move(state)['move']!='right'


def test_pressure_cannot_override_body_collision():
    assert main.evaluate_move(duel(),'down')==-float('inf')


def test_corner_escape_denial():
    state=make_state(you=make_snake(body=[{'x':2,'y':0},{'x':2,'y':1},{'x':3,'y':1}]),enemies=[make_snake('small',body=[{'x':0,'y':0},{'x':0,'y':1}])])
    assert main.score_move_components(state,'left')['aggression'] > 0
