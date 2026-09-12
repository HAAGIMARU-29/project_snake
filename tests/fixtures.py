def make_snake(
    snake_id="you",
    body=None,
    health=100,
    name=None,
):
    if body is None:
        body = [
            {"x": 5, "y": 5},
            {"x": 5, "y": 4},
            {"x": 5, "y": 3},
        ]

    return {
        "id": snake_id,
        "name": name or snake_id,
        "health": health,
        "body": body,
        "head": body[0],
        "length": len(body),
        "latency": "0",
        "shout": "",
    }


def make_state(
    width=11,
    height=11,
    you=None,
    enemies=None,
    food=None,
    hazards=None,
    turn=0,
    ruleset="standard",
):
    if you is None:
        you = make_snake()

    if enemies is None:
        enemies = []

    if food is None:
        food = []

    if hazards is None:
        hazards = []

    return {
        "game": {
            "id": "test-game",
            "ruleset": {
                "name": ruleset,
                "version": "v1.2.3",
                "settings": {},
            },
            "map": "standard",
            "source": "testing",
            "timeout": 500,
        },
        "turn": turn,
        "board": {
            "height": height,
            "width": width,
            "food": food,
            "hazards": hazards,
            "snakes": [you] + enemies,
        },
        "you": you,
    }
