import copy
from time import perf_counter
import pytest
import main
from snake.search import choose_move, simulate_turn, response_penalty, SEARCH_DEATH_PENALTY
from tests.fixtures import make_state, make_snake


def test_disabled_reproduces_heuristic():
    state=make_state(food=[{'x':6,'y':5}])
    scores={m:main.evaluate_move(state,m) for m in main.get_safe_moves(state,True)}
    fallback=max(scores,key=scores.get)
    assert choose_move(state,scores,fallback,enabled=False)==(fallback,{},False)
    assert main.move(state,search_enabled=False)['move']==fallback


def test_expired_deadline_returns_exact_fallback():
    assert choose_move(make_state(),{'up':1},'up',deadline=0)==('up',{},True)


def test_mid_search_deadline_discards_partial_scores():
    ticks=iter([0,0,1])
    assert choose_move(make_state(),{'up':1,'right':2},'right',deadline=0.5,clock=lambda:next(ticks))==('right',{},True)


def test_simulation_multiple_snakes_food_growth_no_mutation():
    state=make_state(food=[{'x':6,'y':5}],enemies=[make_snake('enemy',body=[{'x':9,'y':9},{'x':9,'y':8}])])
    original=copy.deepcopy(state)
    future,reasons=simulate_turn(state,{'you':'right','enemy':'left'})
    assert not reasons
    assert len(future['board']['snakes'])==2
    assert future['you']['health']==100 and future['you']['length']==4
    assert future['you']['body'][-1]==future['you']['body'][-2]
    assert future['board']['food']==[] and state==original


@pytest.mark.parametrize('enemy_length',[3,4])
def test_search_rejects_equal_larger_head_collision(enemy_length):
    enemy=make_snake('enemy',body=[{'x':7,'y':5-i} for i in range(enemy_length)])
    state=make_state(enemies=[enemy])
    future,reasons=simulate_turn(state,{'you':'right','enemy':'left'})
    assert reasons['you']=='HEAD_TO_HEAD'
    # Deliberately misleading static score: search must discover the collision.
    chosen,penalties,_=choose_move(state,{'right':100,'up':0},'right')
    assert chosen=='up' and penalties['right']==-SEARCH_DEATH_PENALTY


def test_search_detects_no_next_exit():
    you=make_snake(body=[{'x':1,'y':1},{'x':1,'y':0},{'x':0,'y':0}])
    wall=make_snake('wall',body=[{'x':3,'y':1},{'x':2,'y':2},{'x':2,'y':0}])
    state=make_state(width=5,height=4,you=you,enemies=[wall])
    assert main.move(state)['move'] in main.get_safe_moves(state,True)
    enclosed=make_state(width=2,height=2,you=make_snake(body=[{'x':0,'y':0},{'x':0,'y':1},{'x':1,'y':1},{'x':1,'y':0},{'x':1,'y':0}]))
    assert response_penalty(enclosed,'you')==-SEARCH_DEATH_PENALTY


def test_search_determinism_legal_no_mutation_and_budget():
    state=make_state()
    original=copy.deepcopy(state)
    started=perf_counter()
    result=main.move(state)
    assert perf_counter()-started < 0.35
    assert result==main.move(state)
    assert result['move'] in main.get_safe_moves(state,True)
    assert state==original


def test_no_scores_never_none():
    assert choose_move(make_state(),{},'down')[0]=='down'
