from contextlib import redirect_stdout
from io import StringIO
from statistics import mean
from time import perf_counter
import pytest
import main
from snake.search import HARD_CUTOFF_SECONDS
from tests.fixtures import integration_scenarios


@pytest.mark.parametrize('name',['crowded_four','territory_split','royale_11','royale_19','long_snake','many_food','many_hazards'])
@pytest.mark.parametrize('search_enabled',[False,True])
def test_move_budget(name,search_enabled):
    state=integration_scenarios()[name]
    durations=[]
    with redirect_stdout(StringIO()):
        for _ in range(8):
            started=perf_counter()
            result=main.move(state,search_enabled=search_enabled)
            durations.append(perf_counter()-started)
            assert result['move'] in main.DIRECTIONS
    # Generous scheduling allowance, plus a meaningful average heuristic target.
    assert max(durations) < HARD_CUTOFF_SECONDS + 0.08
    if not search_enabled:
        assert mean(durations)<0.05
    print(f'{name} search={search_enabled} mean_ms={mean(durations)*1000:.2f} max_ms={max(durations)*1000:.2f}')


def test_extreme_19_board_and_nearby_enemy_search():
    from tests.fixtures import make_state,make_snake,body_at
    extreme=make_state(width=19,height=19,ruleset='royale',food=body_at([(x,y) for x in range(19) for y in range(19) if (x,y) not in {(5,5),(5,4),(5,3)}]),hazards=body_at([(x,y) for x in range(19) for y in range(19)]))
    nearby=make_state(width=19,height=19,ruleset='royale',enemies=[make_snake(str(i),body=body_at(points)) for i,points in enumerate([[(3,6),(2,6),(1,6)],[(7,6),(8,6),(9,6)],[(5,8),(5,9),(5,10)]])])
    for state in (extreme,nearby):
        started=perf_counter()
        main.move(state)
        assert perf_counter()-started < HARD_CUTOFF_SECONDS + 0.08
