import sys
sys.path.insert(0, '/home/sammo/Desktop/SEDS_Hackathon_2026/starter-snake-python')

import main


def test_larger_enemy_contest():
    game_state = {
        'turn': 1,
        'you': {'id': 'me', 'body': [{'x': 5, 'y': 5}, {'x': 5, 'y': 4}, {'x': 5, 'y': 3}, {'x': 5, 'y': 2}, {'x': 5, 'y': 1}]},
        'board': {
            'width': 11, 'height': 11,
            'snakes': [
                {'id': 'me', 'body': [{'x': 5, 'y': 5}, {'x': 5, 'y': 4}, {'x': 5, 'y': 3}, {'x': 5, 'y': 2}, {'x': 5, 'y': 1}]},
                {'id': 'enemy', 'body': [{'x': 7, 'y': 5}, {'x': 7, 'y': 4}, {'x': 7, 'y': 3}, {'x': 7, 'y': 2}, {'x': 7, 'y': 1}, {'x': 7, 'y': 0}, {'x': 6, 'y': 0}, {'x': 5, 'y': 0}]}
            ], 'food': []
        }
    }
    weights = main.build_strategic_weights(game_state)
    assert weights.get((6, 5), 0) == -main.HEAD_DANGER_PENALTY
    safe = main.get_safe_moves(game_state)
    for m in safe:
        blocked = set(main.get_occupied_cells(game_state))
        my_head = main.to_pos(game_state['you']['body'][0])
        blocked.discard(my_head)
        blocked.discard(main.next_position(my_head, m))
        score = main.evaluate_move(game_state, m, blocked, weights)
        if m == 'right':
            assert score < -9000, f"Right move should have massive penalty, got {score}"
        else:
            assert score > 0, f"Other moves should be positive, got {score} for {m}"
    print("test_larger_enemy_contest PASSED")


def test_equal_enemy_contest():
    game_state = {
        'turn': 1,
        'you': {'id': 'me', 'body': [{'x': 5, 'y': 5}, {'x': 5, 'y': 4}, {'x': 5, 'y': 3}, {'x': 5, 'y': 2}, {'x': 5, 'y': 1}]},
        'board': {
            'width': 11, 'height': 11,
            'snakes': [
                {'id': 'me', 'body': [{'x': 5, 'y': 5}, {'x': 5, 'y': 4}, {'x': 5, 'y': 3}, {'x': 5, 'y': 2}, {'x': 5, 'y': 1}]},
                {'id': 'enemy', 'body': [{'x': 7, 'y': 5}, {'x': 7, 'y': 4}, {'x': 7, 'y': 3}, {'x': 7, 'y': 2}, {'x': 7, 'y': 1}]}
            ], 'food': []
        }
    }
    weights = main.build_strategic_weights(game_state)
    assert weights.get((6, 5), 0) == -main.HEAD_DANGER_PENALTY
    safe = main.get_safe_moves(game_state)
    for m in safe:
        blocked = set(main.get_occupied_cells(game_state))
        my_head = main.to_pos(game_state['you']['body'][0])
        blocked.discard(my_head)
        blocked.discard(main.next_position(my_head, m))
        score = main.evaluate_move(game_state, m, blocked, weights)
        if m == 'right':
            assert score < -9000, f"Right move should have massive penalty, got {score}"
        else:
            assert score > 0, f"Other moves should be positive, got {score} for {m}"
    print("test_equal_enemy_contest PASSED")


def test_shorter_enemy_contest():
    game_state = {
        'turn': 1,
        'you': {'id': 'me', 'body': [{'x': 5, 'y': 5}, {'x': 5, 'y': 4}, {'x': 5, 'y': 3}, {'x': 5, 'y': 2}, {'x': 5, 'y': 1}, {'x': 5, 'y': 0}, {'x': 4, 'y': 0}, {'x': 3, 'y': 0}]},
        'board': {
            'width': 11, 'height': 11,
            'snakes': [
                {'id': 'me', 'body': [{'x': 5, 'y': 5}, {'x': 5, 'y': 4}, {'x': 5, 'y': 3}, {'x': 5, 'y': 2}, {'x': 5, 'y': 1}, {'x': 5, 'y': 0}, {'x': 4, 'y': 0}, {'x': 3, 'y': 0}]},
                {'id': 'enemy', 'body': [{'x': 7, 'y': 5}, {'x': 7, 'y': 4}, {'x': 7, 'y': 3}, {'x': 7, 'y': 2}, {'x': 7, 'y': 1}]}
            ], 'food': []
        }
    }
    weights = main.build_strategic_weights(game_state)
    assert weights.get((6, 5), 0) == 0.0, f"Shorter enemy should not apply penalty, got {weights.get((6, 5), 0)}"
    safe = main.get_safe_moves(game_state)
    for m in safe:
        blocked = set(main.get_occupied_cells(game_state))
        my_head = main.to_pos(game_state['you']['body'][0])
        blocked.discard(my_head)
        blocked.discard(main.next_position(my_head, m))
        score = main.evaluate_move(game_state, m, blocked, weights)
        assert score > 0, f"All moves should be positive, got {score} for {m}"
    print("test_shorter_enemy_contest PASSED")


def test_enemy_outside_board():
    game_state = {
        'turn': 1,
        'you': {'id': 'me', 'body': [{'x': 5, 'y': 5}, {'x': 5, 'y': 4}]},
        'board': {
            'width': 11, 'height': 11,
            'snakes': [
                {'id': 'me', 'body': [{'x': 5, 'y': 5}, {'x': 5, 'y': 4}]},
                {'id': 'enemy', 'body': [{'x': 0, 'y': 0}, {'x': 0, 'y': 1}]}
            ], 'food': []
        }
    }
    enemy = game_state['board']['snakes'][1]
    possible = main.get_enemy_possible_head_positions(game_state, enemy)
    assert (0, -1) not in possible
    assert (-1, 0) not in possible
    assert (0, 1) not in possible  # occupied by own body
    assert (1, 0) in possible
    print("test_enemy_outside_board PASSED")


def test_enemy_blocked_by_body():
    game_state = {
        'turn': 1,
        'you': {'id': 'me', 'body': [{'x': 5, 'y': 5}, {'x': 5, 'y': 4}]},
        'board': {
            'width': 11, 'height': 11,
            'snakes': [
                {'id': 'me', 'body': [{'x': 5, 'y': 5}, {'x': 5, 'y': 4}]},
                {'id': 'enemy', 'body': [{'x': 5, 'y': 7}, {'x': 5, 'y': 6}, {'x': 6, 'y': 6}, {'x': 6, 'y': 5}]}
            ], 'food': []
        }
    }
    enemy = game_state['board']['snakes'][1]
    possible = main.get_enemy_possible_head_positions(game_state, enemy)
    assert (5, 6) not in possible
    assert (6, 6) not in possible
    assert (6, 5) not in possible
    assert (6, 7) in possible
    assert (4, 7) in possible
    assert (5, 8) in possible
    print("test_enemy_blocked_by_body PASSED")


def test_multiple_enemies():
    game_state = {
        'turn': 1,
        'you': {'id': 'me', 'body': [{'x': 5, 'y': 3}, {'x': 5, 'y': 2}, {'x': 5, 'y': 1}]},
        'board': {
            'width': 11, 'height': 11,
            'snakes': [
                {'id': 'me', 'body': [{'x': 5, 'y': 3}, {'x': 5, 'y': 2}, {'x': 5, 'y': 1}]},
                {'id': 'enemy1', 'body': [{'x': 5, 'y': 5}, {'x': 5, 'y': 4}]},
                {'id': 'enemy2', 'body': [{'x': 3, 'y': 3}, {'x': 4, 'y': 3}, {'x': 4, 'y': 2}, {'x': 4, 'y': 1}, {'x': 4, 'y': 0}, {'x': 3, 'y': 0}, {'x': 2, 'y': 0}, {'x': 1, 'y': 0}, {'x': 0, 'y': 0}, {'x': 0, 'y': 1}]}
            ], 'food': []
        }
    }
    danger_map = main.build_head_danger_map(game_state)
    weights = main.build_strategic_weights(game_state)
    # enemy1 (len 2) at (5,5) can move to (4,5), (5,6), (6,5)
    # enemy2 (len 10) at (3,3) can move to (2,3), (3,2), (3,4)
    assert danger_map.get((4, 5), 0) == 2
    assert danger_map.get((3, 4), 0) == 10
    assert weights.get((4, 5), 0) == 0.0  # shorter enemy (2 < 3), no penalty
    assert weights.get((3, 4), 0) == -main.HEAD_DANGER_PENALTY  # larger enemy (10 >= 3), penalty
    print("test_multiple_enemies PASSED")


def test_no_enemies():
    game_state = {
        'turn': 1,
        'you': {'id': 'me', 'body': [{'x': 5, 'y': 5}, {'x': 5, 'y': 4}, {'x': 5, 'y': 3}]},
        'board': {'width': 11, 'height': 11, 'snakes': [{'id': 'me', 'body': [{'x': 5, 'y': 5}, {'x': 5, 'y': 4}, {'x': 5, 'y': 3}]}], 'food': []}
    }
    weights = main.build_strategic_weights(game_state)
    assert all(v == 0.0 for v in weights.values())
    result = main.move(game_state)
    assert result["move"] in ["up", "right", "down", "left"]
    print("test_no_enemies PASSED")


def test_strategic_weight_initialization():
    weights = main.initialize_strategic_weights(11, 11)
    assert len(weights) == 121
    assert all(v == 0.0 for v in weights.values())
    weights2 = main.initialize_strategic_weights(5, 5)
    assert len(weights2) == 25
    print("test_strategic_weight_initialization PASSED")


def test_no_mutation():
    game_state = {
        'turn': 1,
        'you': {'id': 'me', 'body': [{'x': 5, 'y': 5}, {'x': 5, 'y': 4}]},
        'board': {
            'width': 11, 'height': 11,
            'snakes': [
                {'id': 'me', 'body': [{'x': 5, 'y': 5}, {'x': 5, 'y': 4}]},
                {'id': 'enemy', 'body': [{'x': 7, 'y': 5}, {'x': 7, 'y': 4}]}
            ], 'food': []
        }
    }
    original_enemy_body = [seg.copy() for seg in game_state['board']['snakes'][1]['body']]
    danger_map1 = main.build_head_danger_map(game_state)
    danger_map2 = main.build_head_danger_map(game_state)
    weights1 = main.build_strategic_weights(game_state)
    weights2 = main.build_strategic_weights(game_state)
    assert game_state['board']['snakes'][1]['body'] == original_enemy_body
    assert danger_map1 == danger_map2
    assert weights1 == weights2
    print("test_no_mutation PASSED")


def test_determinism():
    game_state = {
        'turn': 1,
        'you': {'id': 'me', 'body': [{'x': 5, 'y': 5}, {'x': 5, 'y': 4}]},
        'board': {
            'width': 11, 'height': 11,
            'snakes': [
                {'id': 'me', 'body': [{'x': 5, 'y': 5}, {'x': 5, 'y': 4}]},
                {'id': 'enemy', 'body': [{'x': 7, 'y': 5}, {'x': 7, 'y': 4}]}
            ], 'food': []
        }
    }
    results = [main.move(game_state) for _ in range(5)]
    assert all(r == results[0] for r in results)
    print("test_determinism PASSED")


if __name__ == "__main__":
    test_larger_enemy_contest()
    test_equal_enemy_contest()
    test_shorter_enemy_contest()
    test_enemy_outside_board()
    test_enemy_blocked_by_body()
    test_multiple_enemies()
    test_no_enemies()
    test_strategic_weight_initialization()
    test_no_mutation()
    test_determinism()
    print("\nALL TESTS PASSED")

def test_multiple_enemies_same_cell_uses_max_length():
    game_state = {
        "turn": 1,
        "you": {
            "id": "me",
            "body": [
                {"x": 5, "y": 3},
                {"x": 5, "y": 2},
                {"x": 5, "y": 1},
                {"x": 5, "y": 0},
                {"x": 4, "y": 0},
                {"x": 3, "y": 0},
                {"x": 2, "y": 0},
                {"x": 1, "y": 0},
            ],
        },
        "board": {
            "width": 11,
            "height": 11,
            "food": [],
            "snakes": [
                {
                    "id": "me",
                    "body": [
                        {"x": 5, "y": 3},
                        {"x": 5, "y": 2},
                        {"x": 5, "y": 1},
                        {"x": 5, "y": 0},
                        {"x": 4, "y": 0},
                        {"x": 3, "y": 0},
                        {"x": 2, "y": 0},
                        {"x": 1, "y": 0},
                    ],
                },
                {
                    "id": "short-enemy",
                    "body": [
                        {"x": 4, "y": 5},
                        {"x": 4, "y": 6},
                        {"x": 4, "y": 7},
                        {"x": 4, "y": 8},
                        {"x": 4, "y": 9},
                    ],
                },
                {
                    "id": "long-enemy",
                    "body": [
                        {"x": 6, "y": 5},
                        {"x": 6, "y": 6},
                        {"x": 6, "y": 7},
                        {"x": 7, "y": 7},
                        {"x": 8, "y": 7},
                        {"x": 8, "y": 6},
                        {"x": 8, "y": 5},
                        {"x": 8, "y": 4},
                        {"x": 8, "y": 3},
                        {"x": 8, "y": 2},
                    ],
                },
            ],
        },
    }

    danger = main.build_head_danger_map(game_state)

    assert (5, 5) in danger
    assert danger[(5, 5)] == 10


def test_phase3_functions_do_not_mutate_game_state():
    import copy

    game_state = {
        "turn": 12,
        "you": {
            "id": "me",
            "body": [
                {"x": 5, "y": 5},
                {"x": 5, "y": 4},
                {"x": 5, "y": 3},
            ],
        },
        "board": {
            "width": 11,
            "height": 11,
            "food": [{"x": 1, "y": 1}],
            "snakes": [
                {
                    "id": "me",
                    "body": [
                        {"x": 5, "y": 5},
                        {"x": 5, "y": 4},
                        {"x": 5, "y": 3},
                    ],
                },
                {
                    "id": "enemy",
                    "body": [
                        {"x": 7, "y": 5},
                        {"x": 7, "y": 4},
                        {"x": 7, "y": 3},
                    ],
                },
            ],
        },
    }

    original = copy.deepcopy(game_state)

    main.build_head_danger_map(game_state)
    main.build_strategic_weights(game_state)

    assert game_state == original


def test_evaluate_move_handles_raw_blocked_set():
    game_state = {
        "turn": 1,
        "you": {
            "id": "me",
            "body": [
                {"x": 5, "y": 5},
                {"x": 5, "y": 4},
                {"x": 5, "y": 3},
            ],
        },
        "board": {
            "width": 11,
            "height": 11,
            "food": [],
            "snakes": [
                {
                    "id": "me",
                    "body": [
                        {"x": 5, "y": 5},
                        {"x": 5, "y": 4},
                        {"x": 5, "y": 3},
                    ],
                }
            ],
        },
    }

    blocked = main.get_occupied_cells(game_state)
    weights = main.build_strategic_weights(game_state)

    score = main.evaluate_move(
        game_state,
        "up",
        blocked,
        weights,
    )

    assert isinstance(score, (int, float))
    assert score > 0


def test_move_avoids_losing_head_to_head():
    game_state = {
        "turn": 1,
        "you": {
            "id": "me",
            "body": [
                {"x": 5, "y": 5},
                {"x": 5, "y": 4},
                {"x": 5, "y": 3},
            ],
        },
        "board": {
            "width": 11,
            "height": 11,
            "food": [],
            "snakes": [
                {
                    "id": "me",
                    "body": [
                        {"x": 5, "y": 5},
                        {"x": 5, "y": 4},
                        {"x": 5, "y": 3},
                    ],
                },
                {
                    "id": "enemy",
                    "body": [
                        {"x": 7, "y": 5},
                        {"x": 7, "y": 4},
                        {"x": 7, "y": 3},
                        {"x": 8, "y": 3},
                        {"x": 8, "y": 2},
                        {"x": 8, "y": 1},
                    ],
                },
            ],
        },
    }

    result = main.move(game_state)

    assert result["move"] != "right"
