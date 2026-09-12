import copy
import random
import pytest
import main
from tests.fixtures import make_state,make_snake,body_at


def random_board(seed):
    rng=random.Random(seed)
    size=rng.choice([7,11,19])
    occupied=set()
    snakes=[]
    for i in range(rng.randint(1,4)):
        available=[(x,y) for x in range(size) for y in range(size) if (x,y) not in occupied]
        path=[rng.choice(available)]
        occupied.add(path[0])
        for _ in range(rng.randint(2,size)):
            neighbors=[main.next_position(path[-1],direction) for direction in main.MOVE_PRIORITY]
            neighbors=[p for p in neighbors if main.in_bounds(p,size,size) and p not in occupied]
            if not neighbors:
                break
            path.append(rng.choice(neighbors))
            occupied.add(path[-1])
        snakes.append(make_snake(str(i),body=body_at(path),health=rng.randint(1,100)))
    available=[(x,y) for x in range(size) for y in range(size) if (x,y) not in occupied]
    food=rng.sample(available,min(len(available),rng.randint(0,8)))
    hazards=rng.sample([(x,y) for x in range(size) for y in range(size)],rng.randint(0,size*2))
    return make_state(width=size,height=size,you=snakes[0],enemies=snakes[1:],food=body_at(food),hazards=body_at(hazards),ruleset=rng.choice(['standard','royale']))


@pytest.mark.parametrize('seed',range(40))
def test_randomized_invariants(seed):
    state=random_board(seed)
    original=copy.deepcopy(state)
    width,height=state['board']['width'],state['board']['height']
    blocked=main.get_occupied_cells(state)
    saved=blocked.copy()
    head=main.to_pos(state['you']['body'][0])
    assert 0<=main.flood_fill_space(head,blocked-{head},width,height)<=width*height
    assert 0<=main.count_safe_exits(head,blocked,width,height)<=4
    assert all(main.in_bounds(p,width,height) for p in main.build_strategic_weights(state))
    assert all(main.in_bounds(p,width,height) for p in main.build_head_danger_map(state))
    for direction in main.get_safe_moves(state,True):
        assert main.in_bounds(main.next_position(head,direction),width,height)
        main.evaluate_move(state,direction,blocked)
    result=main.move(state)
    assert result['move'] in main.DIRECTIONS
    assert result==main.move(state)
    assert blocked==saved and state==original
