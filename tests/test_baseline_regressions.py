import pytest
import main
from tests.fixtures import make_state,make_snake,body_at


@pytest.mark.parametrize('head,direction',[((0,5),'left'),((10,5),'right'),((5,10),'up'),((5,0),'down')])
def test_all_walls(head,direction):
    state=make_state(you=make_snake(body=body_at([head])))
    assert direction not in main.get_safe_moves(state)
    assert main.evaluate_move(state,direction)==-float('inf')


@pytest.mark.parametrize('blocked_count',range(5))
def test_all_exit_counts(blocked_count):
    adjacent=[(5,6),(6,5),(5,4),(4,5)]
    assert main.count_safe_exits((5,5),set(adjacent[:blocked_count]),11,11)==4-blocked_count


def test_optional_precomputed_evaluation_equivalence_and_copy():
    state=make_state()
    blocked=main.get_occupied_cells(state)
    saved=blocked.copy()
    weights=main.build_strategic_weights(state)
    assert main.evaluate_move(state,'up')==main.evaluate_move(state,'up',blocked,weights)
    assert blocked==saved
    assert sum(main.score_move_components(state,'up').values())==main.evaluate_move(state,'up')
