"""Real retained Chennai geometry; no SUMO process or provider calls."""
import json
import pytest
from citybrain.chennai.network import PILOT
from citybrain.live.graph import PilotGraph, LiveError, coordinate


@pytest.fixture(scope='module')
def graph():
    return PilotGraph()


def pins(graph):
    m = json.loads((PILOT/'network/metadata.json').read_text())
    path = next(iter(m['routes'].values()))
    return dict(edge=path[0],fraction=.2),dict(edge=path[-1],fraction=.8)


@pytest.mark.parametrize('p', [[True,12],[80,float('nan')],[181,12],[80],None])
def test_invalid_coordinates(p):
    with pytest.raises(LiveError):
        coordinate(p)


def test_real_graph_route(graph):
    a,b = pins(graph)
    result = graph.route(a,b)
    assert result['eta_seconds'] > 0
    assert result['estimated_edges'] == len(result['route'])
    assert result['observed_edges'] == 0
    assert all(y in graph.next[x] for x,y in zip(result['route'],result['route'][1:]))
    assert result['geometry'][0]['coordinates'][0] == graph.point_at(a['edge'],.2)
    assert result['geometry'][-1]['coordinates'][-1] == graph.point_at(b['edge'],.8)


def test_partial_edges_and_no_reverse(graph):
    a,_ = pins(graph)
    eid = a['edge']
    r = graph.route(dict(edge=eid,fraction=.2),dict(edge=eid,fraction=.4))
    assert r['eta_seconds'] == pytest.approx(graph.edges[eid]['length']/graph.edges[eid]['speed']*.2)
    try:
        back = graph.route(dict(edge=eid,fraction=.8),dict(edge=eid,fraction=.2))
    except LiveError as e:
        assert e.code=='UNREACHABLE'
    else:
        assert len(back['route'])>1
        assert back['route'][0]==back['route'][-1]


def test_snapping_requires_direction_when_ambiguous(graph):
    ambiguous = None
    for eid in graph.edges:
        p = graph.point_at(eid,.5)
        try:
            snap = graph.snap(p)
            assert snap['distance_m'] <= 25
        except LiveError as e:
            if e.code=='AMBIGUOUS_DIRECTION_SELECT_EDGE':
                ambiguous = (p,e.detail)
                break
    assert ambiguous
    p,choices = ambiguous
    assert len(choices)>1
    chosen = graph.snap(p,choices[0]['edge'])
    assert chosen['confidence']=='USER_CONFIRMED_DIRECTION'
    with pytest.raises(LiveError,match='INVALID_DIRECTED_EDGE_CHOICE'):
        graph.snap(p,'invented')


def test_offroad_outside_and_closure(graph):
    with pytest.raises(LiveError,match='OUTSIDE_ROUTING_PILOT'):
        graph.snap([80.27,13.08])
    a,b = pins(graph)
    with pytest.raises(LiveError,match='UNREACHABLE'):
        graph.route(a,b,{a['edge']:{'blocked':True}})
    assert all(graph.in_bounds(p) for e in graph.edges.values() for p in e['coordinates'])
