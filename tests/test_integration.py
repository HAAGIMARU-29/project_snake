import copy
import json
import pytest
import main
from tests.fixtures import integration_scenarios


@pytest.mark.parametrize('name,state',integration_scenarios().items())
def test_realistic_complete_move(name,state):
    original=copy.deepcopy(state)
    result=main.move(state)
    assert isinstance(result,dict) and result['move'] in main.DIRECTIONS
    assert json.loads(json.dumps(result))==result
    assert result==main.move(state)
    assert state==original
    legal=main.get_safe_moves(state,tail_aware=True)
    if legal:
        assert result['move'] in legal
    if name in ('food_emergency','many_hazards'):
        assert result['move']=='right'
    if name=='tail_escape':
        assert result['move']=='left'
    if name=='equal_head':
        assert result['move']!='right'
