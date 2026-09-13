import copy

from snake.search import simulate_turn
from tests.fixtures import body_at, make_snake, make_state


def test_simulation_pops_tail_and_preserves_non_eating_length():
    state = make_state(you=make_snake(body=body_at([(2, 2), (2, 1), (1, 1)])))
    future, reasons = simulate_turn(state, {"you": "up"})
    assert reasons == {}
    assert future["you"]["body"] == body_at([(2, 3), (2, 2), (2, 1)])
    assert future["you"]["length"] == 3
    assert state["you"]["body"] == body_at([(2, 2), (2, 1), (1, 1)])


def test_simulation_food_resets_health_and_grows():
    state = make_state(
        you=make_snake(health=4, body=body_at([(2, 2), (2, 1), (1, 1)])),
        food=body_at([(2, 3)]),
    )
    future, reasons = simulate_turn(state, {"you": "up"})
    assert reasons == {}
    assert future["you"]["health"] == 100
    assert future["you"]["length"] == 4
    assert future["you"]["body"][-1] == future["you"]["body"][-2]
    assert future["board"]["food"] == []


def test_simulation_hazard_damage_can_eliminate():
    state = make_state(
        ruleset="royale",
        you=make_snake(health=10),
        hazards=body_at([(5, 6)]),
    )
    future, reasons = simulate_turn(state, {"you": "up"})
    assert reasons["you"] == "HAZARD"
    assert future["board"]["snakes"] == []


def test_food_on_hazard_resets_before_damage():
    state = make_state(
        ruleset="royale",
        you=make_snake(health=1),
        food=body_at([(5, 6)]),
        hazards=body_at([(5, 6)]),
    )
    future, reasons = simulate_turn(state, {"you": "up"})
    assert reasons == {}
    assert future["you"]["health"] == 100


def test_equal_head_collision_eliminates_both():
    state = make_state(
        you=make_snake(body=body_at([(5, 5), (5, 4), (5, 3)])),
        enemies=[make_snake("enemy", body=body_at([(5, 7), (5, 8), (5, 9)]))],
    )
    future, reasons = simulate_turn(state, {"you": "up", "enemy": "down"})
    assert reasons == {"you": "HEAD_TO_HEAD", "enemy": "HEAD_TO_HEAD"}
    assert future["board"]["snakes"] == []


def test_longer_head_wins_and_shorter_is_removed():
    state = make_state(
        you=make_snake(body=body_at([(5, 5), (5, 4), (5, 3), (4, 3)])),
        enemies=[make_snake("enemy", body=body_at([(5, 7), (5, 8), (5, 9)]))],
    )
    future, reasons = simulate_turn(state, {"you": "up", "enemy": "down"})
    assert reasons == {"enemy": "HEAD_TO_HEAD"}
    assert [snake["id"] for snake in future["board"]["snakes"]] == ["you"]


def test_body_collision_is_checked_after_simultaneous_movement():
    state = make_state(
        you=make_snake(body=body_at([(5, 5), (5, 4), (5, 3)])),
        enemies=[make_snake("enemy", body=body_at([(6, 6), (6, 5), (7, 5)]))],
    )
    future, reasons = simulate_turn(state, {"you": "right", "enemy": "up"})
    assert reasons["you"] == "BODY"
    assert [snake["id"] for snake in future["board"]["snakes"]] == ["enemy"]


def test_simulation_does_not_mutate_any_input_objects():
    state = make_state(
        you=make_snake(health=40),
        enemies=[make_snake("enemy", body=body_at([(8, 8), (8, 7)]))],
        food=body_at([(6, 5)]),
    )
    original = copy.deepcopy(state)
    moves = {"you": "right", "enemy": "left"}
    simulate_turn(state, moves)
    assert state == original
    assert moves == {"you": "right", "enemy": "left"}


def test_missing_moves_use_deterministic_fallback():
    state = make_state()
    first, _ = simulate_turn(state, {})
    second, _ = simulate_turn(state, {})
    assert first == second
