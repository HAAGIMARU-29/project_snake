from main import (
    flood_fill_space,
    count_safe_exits,
    evaluate_move,
    get_safe_moves,
)

from tests.fixtures import make_snake, make_state


def test_open_board_flood_fill_counts_all_cells():
    blocked = set()

    space = flood_fill_space(
        start=(5, 5),
        blocked=blocked,
        width=11,
        height=11,
    )

    assert space == 121


def test_flood_fill_respects_board_boundaries():
    blocked = set()

    space = flood_fill_space(
        start=(0, 0),
        blocked=blocked,
        width=3,
        height=3,
    )

    assert space == 9


def test_flood_fill_does_not_cross_blocked_cells():
    blocked = {
        (1, 0),
        (1, 1),
        (1, 2),
    }

    space = flood_fill_space(
        start=(0, 1),
        blocked=blocked,
        width=3,
        height=3,
    )

    assert space == 3


def test_flood_fill_handles_candidate_head_if_removed_from_blocked():
    blocked = {
        (1, 1),
    }

    blocked_for_eval = blocked.copy()
    blocked_for_eval.discard((1, 1))

    space = flood_fill_space(
        start=(1, 1),
        blocked=blocked_for_eval,
        width=3,
        height=3,
    )

    assert space == 9


def test_count_safe_exits_open_center():
    blocked = set()

    exits = count_safe_exits(
        pos=(5, 5),
        blocked=blocked,
        width=11,
        height=11,
    )

    assert exits == 4


def test_count_safe_exits_corner():
    blocked = set()

    exits = count_safe_exits(
        pos=(0, 0),
        blocked=blocked,
        width=11,
        height=11,
    )

    assert exits == 2


def test_count_safe_exits_with_three_blocked_neighbors():
    blocked = {
        (5, 6),
        (6, 5),
        (5, 4),
    }

    exits = count_safe_exits(
        pos=(5, 5),
        blocked=blocked,
        width=11,
        height=11,
    )

    assert exits == 1


def test_count_safe_exits_zero_when_completely_surrounded():
    blocked = {
        (5, 6),
        (6, 5),
        (5, 4),
        (4, 5),
    }

    exits = count_safe_exits(
        pos=(5, 5),
        blocked=blocked,
        width=11,
        height=11,
    )

    assert exits == 0


def test_safe_moves_still_respect_phase1_collision_logic():
    you = make_snake(
        body=[
            {"x": 5, "y": 5},
            {"x": 5, "y": 4},
            {"x": 5, "y": 3},
        ]
    )

    enemy = make_snake(
        snake_id="enemy",
        body=[
            {"x": 6, "y": 5},
            {"x": 7, "y": 5},
        ]
    )

    state = make_state(
        you=you,
        enemies=[enemy],
    )

    moves = get_safe_moves(state)

    assert "down" not in moves
    assert "right" not in moves


def test_evaluate_move_prefers_more_open_space():
    you = make_snake(
        body=[
            {"x": 2, "y": 2},
            {"x": 2, "y": 1},
            {"x": 2, "y": 0},
        ]
    )

    enemies = [
        make_snake(
            snake_id="wall-a",
            body=[
                {"x": 4, "y": 0},
                {"x": 4, "y": 1},
                {"x": 4, "y": 2},
                {"x": 4, "y": 3},
                {"x": 4, "y": 4},
            ],
        )
    ]

    state = make_state(
        width=7,
        height=5,
        you=you,
        enemies=enemies,
    )

    up_score = evaluate_move(state, "up")
    right_score = evaluate_move(state, "right")

    assert up_score > right_score


def test_evaluate_move_penalizes_dead_end():
    you = make_snake(
        body=[
            {"x": 2, "y": 2},
            {"x": 2, "y": 1},
            {"x": 2, "y": 0},
        ]
    )

    enemies = [
        make_snake(
            snake_id="blocker-1",
            body=[
                {"x": 4, "y": 2},
                {"x": 3, "y": 3},
                {"x": 3, "y": 1},
            ],
        )
    ]

    state = make_state(
        width=7,
        height=5,
        you=you,
        enemies=enemies,
    )

    right_score = evaluate_move(state, "right")
    up_score = evaluate_move(state, "up")

    assert up_score > right_score


def test_evaluate_move_heavily_penalizes_region_smaller_than_snake():
    you = make_snake(
        body=[
            {"x": 1, "y": 1},
            {"x": 1, "y": 0},
            {"x": 0, "y": 0},
            {"x": 0, "y": 1},
            {"x": 0, "y": 2},
        ]
    )

    enemy = make_snake(
        snake_id="wall",
        body=[
            {"x": 2, "y": 0},
            {"x": 2, "y": 1},
            {"x": 2, "y": 2},
            {"x": 2, "y": 3},
        ]
    )

    state = make_state(
        width=5,
        height=4,
        you=you,
        enemies=[enemy],
    )

    up_score = evaluate_move(state, "up")

    assert up_score < 0


def test_evaluate_move_is_deterministic():
    state = make_state()

    first = evaluate_move(state, "up")
    second = evaluate_move(state, "up")

    assert first == second


def test_evaluate_move_returns_numeric_score():
    state = make_state()

    score = evaluate_move(state, "up")

    assert isinstance(score, (int, float))


def test_tie_break_behavior_can_remain_deterministic():
    you = make_snake(
        body=[
            {"x": 5, "y": 5},
            {"x": 5, "y": 4},
            {"x": 5, "y": 3},
        ]
    )

    state = make_state(
        width=11,
        height=11,
        you=you,
    )

    up_score = evaluate_move(state, "up")
    right_score = evaluate_move(state, "right")

    assert isinstance(up_score, (int, float))
    assert isinstance(right_score, (int, float))


def test_flood_fill_does_not_mutate_blocked_set():
    blocked = {
        (1, 1),
        (2, 2),
    }

    original = blocked.copy()

    flood_fill_space(
        start=(0, 0),
        blocked=blocked,
        width=4,
        height=4,
    )

    assert blocked == original


def test_count_safe_exits_does_not_mutate_blocked_set():
    blocked = {
        (5, 6),
        (6, 5),
    }

    original = blocked.copy()

    count_safe_exits(
        pos=(5, 5),
        blocked=blocked,
        width=11,
        height=11,
    )

    assert blocked == original
