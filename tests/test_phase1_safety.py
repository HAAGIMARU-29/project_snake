from main import get_safe_moves, in_bounds, next_position, move
from tests.fixtures import make_snake, make_state


def test_in_bounds_valid_positions():
    assert in_bounds((0, 0), 11, 11)
    assert in_bounds((10, 10), 11, 11)
    assert in_bounds((5, 5), 11, 11)


def test_in_bounds_rejects_invalid_positions():
    assert not in_bounds((-1, 0), 11, 11)
    assert not in_bounds((0, -1), 11, 11)
    assert not in_bounds((11, 0), 11, 11)
    assert not in_bounds((0, 11), 11, 11)


def test_next_position_directions():
    origin = (5, 5)

    assert next_position(origin, "up") == (5, 6)
    assert next_position(origin, "down") == (5, 4)
    assert next_position(origin, "left") == (4, 5)
    assert next_position(origin, "right") == (6, 5)


def test_wall_avoidance_left_wall():
    snake = make_snake(
        body=[
            {"x": 0, "y": 5},
            {"x": 1, "y": 5},
            {"x": 2, "y": 5},
        ]
    )

    state = make_state(you=snake)

    assert "left" not in get_safe_moves(state)


def test_own_body_collision():
    snake = make_snake(
        body=[
            {"x": 5, "y": 5},
            {"x": 5, "y": 4},
            {"x": 4, "y": 4},
            {"x": 4, "y": 5},
        ]
    )

    state = make_state(you=snake)

    assert "left" not in get_safe_moves(state)


def test_enemy_body_collision():
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
            {"x": 8, "y": 5},
        ]
    )

    state = make_state(you=you, enemies=[enemy])

    assert "right" not in get_safe_moves(state)


def test_corner_position_filters_walls():
    snake = make_snake(
        body=[
            {"x": 0, "y": 0},
            {"x": 0, "y": 1},
            {"x": 1, "y": 1},
        ]
    )

    state = make_state(you=snake)

    safe_moves = get_safe_moves(state)

    assert "left" not in safe_moves
    assert "down" not in safe_moves


def test_move_returns_valid_direction():
    state = make_state()
    result = move(state)

    assert result["move"] in {
        "up",
        "down",
        "left",
        "right",
    }


def test_move_is_deterministic():
    state = make_state()

    assert move(state)["move"] == move(state)["move"]


def test_no_safe_move_does_not_crash():
    you = make_snake(
        body=[
            {"x": 5, "y": 5},
            {"x": 5, "y": 4},
        ]
    )

    enemies = [
        make_snake(
            snake_id="enemy-up",
            body=[{"x": 5, "y": 6}],
        ),
        make_snake(
            snake_id="enemy-right",
            body=[{"x": 6, "y": 5}],
        ),
        make_snake(
            snake_id="enemy-left",
            body=[{"x": 4, "y": 5}],
        ),
    ]

    state = make_state(you=you, enemies=enemies)

    assert get_safe_moves(state) == []

    result = move(state)

    assert result["move"] in {
        "up",
        "down",
        "left",
        "right",
    }
