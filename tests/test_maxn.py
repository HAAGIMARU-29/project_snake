import copy

import main
from snake.search import iterative_deepening_search, maxn_root
from tests.fixtures import make_snake, make_state


def nearby_state():
    return make_state(enemies=[
        make_snake("left-enemy", body=[{"x": 2, "y": 5}, {"x": 2, "y": 4}]),
        make_snake("right-enemy", body=[{"x": 8, "y": 5}, {"x": 8, "y": 4}]),
    ])


def test_multiple_relevant_enemies_dispatch_to_maxn():
    state = nearby_state()
    result = iterative_deepening_search(state, "up", 10**9, max_depth=1)
    assert result.algorithm == "maxn"
    assert result.completed_depth == 1
    assert result.move in main.get_safe_moves(state, tail_aware=True)
    assert len(result.vector) == 3


def test_maxn_vector_has_one_component_per_player():
    state = nearby_state()
    result = maxn_root(state, ["you", "left-enemy", "right-enemy"], 1, 10**9)
    assert len(result.vector) == 3
    assert result.score == result.vector[0]
    assert result.algorithm == "maxn"


def test_maxn_is_deterministic_and_non_mutating():
    state = nearby_state()
    original = copy.deepcopy(state)
    first = iterative_deepening_search(state, "up", 10**9, max_depth=2)
    second = iterative_deepening_search(state, "up", 10**9, max_depth=2)
    assert first == second
    assert state == original


def test_maxn_does_not_use_alpha_beta_cutoff():
    state = nearby_state()
    result = maxn_root(state, ["you", "left-enemy", "right-enemy"], 1, 10**9)
    # Three players with three or more choices require more than one branch;
    # nodes are exposed for instrumentation rather than hidden in a cutoff.
    assert result.nodes >= 9


def test_distant_snakes_are_not_full_maxn_players():
    state = nearby_state()
    state["board"]["snakes"].append(
        make_snake("distant", body=[{"x": 0, "y": 0}, {"x": 0, "y": 1}])
    )
    result = iterative_deepening_search(state, "up", 10**9, max_depth=1)
    assert result.algorithm == "maxn"
    assert len(result.vector) == 3


def test_maxn_expired_deadline_returns_fallback_without_partial_depth():
    result = iterative_deepening_search(nearby_state(), "left", 0, max_depth=3)
    assert result.move == "left"
    assert result.completed_depth == 0
    assert result.timed_out


def test_single_relevant_enemy_uses_alpha_beta():
    state = make_state(enemies=[make_snake("enemy", body=[{"x": 7, "y": 5}, {"x": 7, "y": 4}])])
    result = iterative_deepening_search(state, "up", 10**9, max_depth=1)
    assert result.algorithm == "alphabeta"
