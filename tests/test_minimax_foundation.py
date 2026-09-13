import copy

import main
from snake.search import (
    SearchResult,
    deadline_expired,
    evaluate_search_state,
    fingerprint_state,
    generate_search_moves,
    select_relevant_snakes,
)
from tests.fixtures import make_snake, make_state


def test_search_result_has_safe_fallback_defaults():
    result = SearchResult(move="up", score=12.5)
    assert result.completed_depth == 0
    assert result.nodes == 0
    assert result.algorithm == "fallback"
    assert not result.timed_out


def test_deadline_helper_uses_injected_clock():
    assert deadline_expired(10, clock=lambda: 9) is False
    assert deadline_expired(10, clock=lambda: 10) is True
    assert deadline_expired(None, clock=lambda: 10) is False


def test_relevant_snakes_use_nearest_body_distance_and_stable_order():
    near = make_snake("near", body=[{"x": 7, "y": 5}, {"x": 8, "y": 5}])
    far_head_near_body = make_snake("body-near", body=[{"x": 10, "y": 10}, {"x": 6, "y": 5}])
    far = make_snake("far", body=[{"x": 10, "y": 10}, {"x": 10, "y": 9}])
    state = make_state(enemies=[far, far_head_near_body, near])
    selected = select_relevant_snakes(state, max_distance=2, horizon=2)
    assert [snake["id"] for snake in selected] == ["body-near", "near"]
    assert select_relevant_snakes(state, max_distance=2, horizon=2) == selected


def test_relevance_horizon_can_be_tightened():
    enemy = make_snake("enemy", body=[{"x": 9, "y": 5}, {"x": 8, "y": 5}])
    state = make_state(enemies=[enemy])
    assert select_relevant_snakes(state, max_distance=1, horizon=2) == []
    assert [s["id"] for s in select_relevant_snakes(state, max_distance=2, horizon=2)] == ["enemy"]


def test_generate_search_moves_uses_enemy_perspective_without_mutation():
    enemy = make_snake("enemy", body=[{"x": 7, "y": 5}, {"x": 7, "y": 4}])
    state = make_state(enemies=[enemy])
    original = copy.deepcopy(state)
    moves = generate_search_moves(state, "enemy")
    assert moves == ["up", "right", "left"]
    assert state == original
    assert generate_search_moves(state, "missing") == []


def test_fingerprint_is_hashable_stable_and_perspective_sensitive():
    state = make_state(ruleset="royale")
    first = fingerprint_state(state)
    second = fingerprint_state(copy.deepcopy(state))
    assert first == second
    assert hash(first)
    assert first != fingerprint_state(state, perspective_id="enemy")
    changed = copy.deepcopy(state)
    changed["you"]["health"] = 99
    assert first != fingerprint_state(changed)


def test_fingerprint_includes_rules_and_board_dimensions():
    standard = fingerprint_state(make_state())
    royale = fingerprint_state(make_state(ruleset="royale"))
    larger = fingerprint_state(make_state(width=19, height=19))
    assert standard != royale
    assert standard != larger


def test_fingerprint_handles_nested_rule_settings():
    state = make_state(ruleset="royale")
    state["game"]["ruleset"]["settings"] = {
        "hazardDamagePerTurn": 14,
        "royale": {"shrinkEveryNTurns": 25},
    }
    assert hash(fingerprint_state(state))


def test_search_leaf_evaluation_is_root_relative_and_non_mutating():
    state = make_state(enemies=[make_snake("enemy")])
    original = copy.deepcopy(state)
    score = evaluate_search_state(state, root_id="you", player_ids=["you", "enemy"])
    assert score > 0
    assert evaluate_search_state(state, root_id="missing", player_ids=["you"]) == -main.HEAD_DANGER_PENALTY * 2
    assert state == original


def test_leaf_evaluation_penalizes_small_regions():
    you = make_snake(body=[{"x": 1, "y": 1}, {"x": 1, "y": 0}, {"x": 0, "y": 0}])
    wall = make_snake("wall", body=[{"x": 2, "y": 1}, {"x": 2, "y": 0}])
    state = make_state(width=3, height=2, you=you, enemies=[wall])
    assert evaluate_search_state(state, root_id="you") >= 0
