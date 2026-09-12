import json
import pytest
import main
from tests.fixtures import make_state


@pytest.mark.parametrize('cause,expected',[('wall-collision','WALL'),('snake-collision','BODY'),('snake-self-collision','BODY'),('head-collision','HEAD_TO_HEAD'),('out-of-health','STARVATION'),('hazard','HAZARD'),('timeout','TIMEOUT'),('trapped','TRAPPED'),('','UNKNOWN')])
def test_death_categories(cause,expected):
    state=make_state()
    state['you']['elimination_event']={'cause':cause}
    assert main.death_reason(state)==expected


def test_compact_decision_logging(capsys,monkeypatch):
    monkeypatch.setenv('BATTLESNAKE_LOG','1')
    state=make_state()
    result=main.move(state)
    line=capsys.readouterr().out.strip()
    logged=json.loads(line)
    assert logged['chosen_move']==result['move']
    assert logged['decision_time_ms']>=0
    assert logged['snakes_alive']==1 and logged['health']==100
    assert logged['ruleset']=='standard' and 'search' in logged['scores']
    assert len(line)<1000


def test_environment_disables_search(monkeypatch):
    monkeypatch.setenv('BATTLESNAKE_SEARCH','0')
    assert main.move(make_state())==main.move(make_state(),search_enabled=False)


def test_supplied_weights_cannot_cancel_head_penalty():
    from tests.fixtures import make_snake,body_at
    state=make_state(enemies=[make_snake('enemy',body=body_at([(7,5),(7,4),(7,3)]))])
    assert main.evaluate_move(state,'right',strategic_weights={(6,5):1e20}) < -9000


def test_vacating_own_tail_still_has_head_danger():
    from tests.fixtures import make_snake,body_at
    you=make_snake(body=body_at([(5,5),(5,4),(4,4),(4,5)]))
    enemy=make_snake('enemy',body=body_at([(3,5),(3,4),(3,3),(3,2)]))
    state=make_state(you=you,enemies=[enemy])
    assert 'left' in main.get_safe_moves(state,True)
    assert main.build_head_danger_map(state)[(4,5)]==4
    assert main.move(state,search_enabled=False)['move']!='left'


def test_flask_routes_remain_compatible(monkeypatch):
    import flask
    import server
    app=flask.Flask('test')
    monkeypatch.setattr(server,'Flask',lambda *args:app)
    monkeypatch.setattr(app,'run',lambda **kwargs:None)
    server.run_server({'info':main.info,'start':main.start,'move':main.move,'end':main.end})
    # Flask 2.3.2 test_client reads removed Werkzeug version metadata.
    # Exercise the actual WSGI app through Werkzeug's supported client.
    from werkzeug.test import Client
    client=Client(app,flask.Response)
    assert client.get('/').json['apiversion']=='1'
    state=make_state()
    assert client.post('/start',json=state).status_code==200
    response=client.post('/move',json=state)
    assert response.status_code==200 and response.json['move'] in main.DIRECTIONS
    assert 'battlesnake' in response.headers['server']
    assert client.post('/end',json=state).status_code==200


def test_search_finds_escape_missed_by_real_heuristic():
    from pathlib import Path
    from snake.search import choose_move
    state=json.loads((Path(__file__).parent/'tactical_regression.json').read_text())
    weights=main.build_strategic_weights(state)
    scores={m:main.evaluate_move(state,m,strategic_weights=weights) for m in main.get_safe_moves(state,True)}
    fallback=max(scores,key=scores.get)
    assert fallback=='up'
    assert main.score_move_components(state,fallback)['trap']==0
    chosen,penalties,timed_out=choose_move(state,scores,fallback)
    assert not timed_out and chosen=='down'
    assert penalties['up']==-20000 and penalties['down']>-20000
    assert main.move(state)['move']=='down'


def test_starvation_uses_hazard_energy_not_geometric_reachability():
    from tests.fixtures import make_snake,body_at
    state=make_state(ruleset='royale',you=make_snake(health=10),
                     food=body_at([(8,5)]),hazards=body_at([(7,y) for y in range(11)]))
    parts=main.score_move_components(state,'right')
    assert parts['food']==0 and parts['starvation']<0
