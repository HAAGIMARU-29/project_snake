import copy

import main
import snake.search as search
from snake.search import (
    SEARCH_DEATH_PENALTY,
    SearchResult,
    alpha_beta_root,
    iterative_deepening_search,
)
from tests.fixtures import make_snake, make_state


def test_alpha_beta_returns_legal_move_and_completed_depth():
    enemy = make_snake("enemy", body=[{"x": 7, "y": 5}, {"x": 7, "y": 4}, {"x": 7, "y": 3}])
    state = make_state(enemies=[enemy])
    result = iterative_deepening_search(state, "up", 10**9, max_depth=2)
    assert isinstance(result, SearchResult)
    assert result.algorithm == "alphabeta"
    assert result.completed_depth == 2
    assert result.move in main.get_safe_moves(state, tail_aware=True)
    assert result.nodes > 0


def test_alpha_beta_prefers_safe_response_when_heuristic_is_misleading():
    enemy = make_snake("enemy", body=[{"x": 7, "y": 5}, {"x": 7, "y": 4}, {"x": 7, "y": 3}, {"x": 8, "y": 3}])
    state = make_state(enemies=[enemy])
    result = iterative_deepening_search(state, "right", 10**9, max_depth=2)
    assert result.move != "right"


def test_alpha_beta_is_deterministic_and_does_not_mutate_state():
    state = make_state(enemies=[make_snake("enemy", body=[{"x": 7, "y": 5}, {"x": 7, "y": 4}])])
    original = copy.deepcopy(state)
    first = iterative_deepening_search(state, "up", 10**9, max_depth=2)
    second = iterative_deepening_search(state, "up", 10**9, max_depth=2)
    assert first == second
    assert state == original


def test_alpha_beta_expired_deadline_keeps_fallback_and_depth_zero():
    state = make_state(enemies=[make_snake("enemy")])
    result = iterative_deepening_search(state, "left", 0, max_depth=4)
    assert result.move == "left"
    assert result.completed_depth == 0
    assert result.timed_out


def test_alpha_beta_injected_clock_discards_partial_depth():
    state = make_state(enemies=[make_snake("enemy")])
    ticks = iter([0, 0, 0, 2])
    result = iterative_deepening_search(state, "down", 1, max_depth=3, clock=lambda: next(ticks))
    assert result.move == "down"
    assert result.completed_depth == 0
    assert result.timed_out


def test_iterative_deepening_keeps_last_completed_depth(monkeypatch):
    state = make_state(enemies=[make_snake("enemy")])
    calls = []

    def staged_root(*args, **kwargs):
        calls.append(args[3])
        if len(calls) == 1:
            return SearchResult("right", 42.0, completed_depth=1, nodes=7, algorithm="alphabeta")
        raise search._SearchTimeout

    monkeypatch.setattr(search, "alpha_beta_root", staged_root)
    result = iterative_deepening_search(state, "down", 10**9, max_depth=3)

    assert calls == [1, 2]
    assert result.move == "right"
    assert result.completed_depth == 1
    assert result.nodes == 7
    assert result.timed_out


def test_alpha_beta_table_is_local_and_cache_hits_are_reported():
    state = make_state(enemies=[make_snake("enemy")])
    table = {}
    first = alpha_beta_root(state, "you", "enemy", 2, 10**9, table=table)
    second = alpha_beta_root(state, "you", "enemy", 2, 10**9, table=table)
    assert first.move == second.move
    assert len(table) > 0
    assert second.cache_hits >= first.cache_hits


def test_no_relevant_enemy_preserves_fallback_algorithm():
    state = make_state(enemies=[make_snake("far", body=[{"x": 10, "y": 10}, {"x": 10, "y": 9}])])
    result = iterative_deepening_search(state, "right", 10**9, max_depth=3)
    assert result.move == "right"
    assert result.algorithm == "fallback"


def test_terminal_alpha_beta_value_is_large_negative():
    state = make_state(enemies=[make_snake("enemy", body=[{"x": 9, "y": 9}, {"x": 9, "y": 8}])])
    result = alpha_beta_root(state, "you", "enemy", 1, 10**9)
    assert result.score > -SEARCH_DEATH_PENALTY
