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


def body_at(points):
    return [{'x':x,'y':y} for x,y in points]


def integration_scenarios():
    """Representative scenarios shared by integration and performance checks."""
    import copy
    enemies = [make_snake(str(i),body=body_at([(x,y),(x,y-1),(x,y-2)]))
               for i,(x,y) in enumerate([(2,8),(8,8),(8,3)])]
    scenarios = {'open_standard':make_state(), 'crowded_four':make_state(enemies=enemies)}
    scenarios['food_emergency']=make_state(you=make_snake(health=2),food=body_at([(6,5)]))
    scenarios['equal_head']=make_state(enemies=[make_snake('enemy',body=body_at([(7,5),(7,4),(7,3)]))])
    loop=make_snake(body=body_at([(5,5),(5,4),(4,4),(4,5)]))
    scenarios['tail_escape']=make_state(you=loop,enemies=[make_snake('wall',body=body_at([(5,6),(6,5)]))])
    scenarios['enemy_tail']=make_state(enemies=[make_snake('enemy',body=body_at([(7,5),(7,4),(6,4),(6,5)]))],food=body_at([(7,6)]))
    scenarios['territory_split']=make_state(enemies=[make_snake('wall',body=body_at([(7,y) for y in range(11)]))])
    scenarios['duel']=make_state(enemies=enemies[:1],food=body_at([(4,6),(3,8)]))
    for size in [11,19]:
        scenarios[f'royale_{size}']=make_state(width=size,height=size,enemies=copy.deepcopy(enemies),ruleset='royale',
            hazards=body_at([(x,y) for x in range(size) for y in range(size) if x<2 or y<2]),food=body_at([(6,5),(3,6)]))
    scenarios['trapped']=make_state(enemies=[make_snake('wall',body=body_at([(5,6),(6,5),(4,5)]))])
    scenarios['no_food']=make_state(enemies=copy.deepcopy(enemies))
    occupied={(cell['x'],cell['y']) for cell in make_snake()['body']}
    scenarios['many_food']=make_state(food=body_at([(x,y) for x in range(11) for y in range(11) if (x,y) not in occupied]))
    scenarios['many_hazards']=make_state(ruleset='royale',hazards=body_at([(x,y) for x in range(11) for y in range(11)]),food=body_at([(6,5)]))
    path=[(x,y) for y in range(6) for x in (range(11) if y%2==0 else reversed(range(11)))]
    scenarios['long_snake']=make_state(you=make_snake(body=body_at(list(reversed(path)))))
    scenarios['simultaneous_threats']=copy.deepcopy(scenarios['royale_11'])
    scenarios['simultaneous_threats']['you']['health']=18
    return scenarios
