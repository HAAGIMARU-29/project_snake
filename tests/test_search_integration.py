import json

import main
from tests.fixtures import make_snake, make_state


def test_live_move_reports_completed_alpha_beta_depth(capsys, monkeypatch):
    monkeypatch.setenv("BATTLESNAKE_LOG", "1")
    state = make_state(enemies=[make_snake("enemy", body=[{"x": 7, "y": 5}, {"x": 7, "y": 4}])])
    result = main.move(state)
    payload = json.loads(capsys.readouterr().out.strip())
    assert result["move"] in main.get_safe_moves(state, tail_aware=True)
    assert payload["search_depth"] >= 1
    assert payload["search_nodes"] > 0
    assert payload["chosen_move"] == result["move"]


def test_live_move_reports_maxn_for_multiple_nearby_enemies(capsys, monkeypatch):
    monkeypatch.setenv("BATTLESNAKE_LOG", "1")
    state = make_state(enemies=[
        make_snake("enemy-a", body=[{"x": 2, "y": 5}, {"x": 2, "y": 4}]),
        make_snake("enemy-b", body=[{"x": 8, "y": 5}, {"x": 8, "y": 4}]),
    ])
    result = main.move(state)
    payload = json.loads(capsys.readouterr().out.strip())
    assert result["move"] in main.get_safe_moves(state, tail_aware=True)
    assert payload["search_depth"] >= 1
    assert payload["search_nodes"] >= 9


def test_live_max_depth_environment_is_bounded_and_deterministic(monkeypatch):
    state = make_state(enemies=[make_snake("enemy", body=[{"x": 7, "y": 5}, {"x": 7, "y": 4}])])
    monkeypatch.setenv("BATTLESNAKE_MAX_DEPTH", "1")
    first = main.move(state)
    second = main.move(state)
    assert first == second


def test_search_disabled_preserves_heuristic_selection(monkeypatch):
    state = make_state(enemies=[make_snake("enemy", body=[{"x": 7, "y": 5}, {"x": 7, "y": 4}])])
    monkeypatch.setenv("BATTLESNAKE_SEARCH", "0")
    disabled = main.move(state)
    explicit = main.move(state, search_enabled=False)
    assert disabled == explicit
