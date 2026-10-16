"""Longitudinal coverage regressions: endpoint distance is not road overlap."""
from test_chennai_traffic import Edge, Net, Provider, NOW, observation
from citybrain.chennai.traffic.matching import RoadMatcher
from citybrain.chennai.traffic.provider import FetchResult
from citybrain.chennai.traffic.service import TrafficService


def test_exact_review_40m_provider_cannot_match_10m_road():
    row = observation(road_geometry=((.0003,0),(.0007,0)),source_type='HERE_LIVE')
    matcher = RoadMatcher(Net([Edge('tiny',[(45,0),(55,0)])]))
    result = matcher.match(row)
    assert result.matching_status == 'UNMATCHED'
    assert not result.matched_sumo_edges
    service = TrafficService(Provider(FetchResult([row],'FETCHED')),matcher,clock=lambda:NOW)
    service.poll_once()
    assert service.snapshot()['display_status'] != 'LIVE DATA'


import pytest
from citybrain.chennai.network import read_network


@pytest.mark.parametrize('road,expected',[
    ([(45,0),(55,0)],.25),
    ([(30,0),(60,0)],.75),
    ([(40,0),(70,0)],.75),
    ([(34,0),(70,0)],.90),
])
def test_partial_longitudinal_overlap_is_rejected(road,expected):
    result = RoadMatcher(Net([Edge('partial',road)])).match(
        observation(road_geometry=((.0003,0),(.0007,0))))
    assert result.matching_status == 'UNMATCHED'
    assert result.matching_coverage == pytest.approx(expected)
    assert 'longitudinal coverage' in result.match_reason
    assert not result.matched_sumo_edges


@pytest.mark.parametrize('road,expected',[
    ([(0,0),(100,0)],1),  # A provider fragment fully inside a longer road is valid.
    ([(31,0),(69,0)],.95),  # Only the documented small uncovered fraction is allowed.
    ([(0,8),(100,8)],1),  # Lateral offset does not invent or remove longitudinal extent.
])
def test_supported_partial_road_extent_and_small_endpoint_noise(road,expected):
    result = RoadMatcher(Net([Edge('road',road)])).match(
        observation(road_geometry=((.0003,0),(.0007,0))))
    assert result.matching_status == 'MATCHED'
    assert result.matching_coverage == pytest.approx(expected)


def test_curved_connected_multi_edge_coverage():
    second = Edge('b',[(50,0),(100,25)])
    first = Edge('a',[(0,0),(50,0)],[second])
    result = RoadMatcher(Net([first,second])).match(
        observation(road_geometry=((0,0),(.0005,0),(.001,.00025))))
    assert result.matching_status == 'MATCHED'
    assert result.matched_sumo_edges == ('a','b')
    assert result.matching_coverage == pytest.approx(1)


@pytest.mark.parametrize('value',[0,-1,1.01,float('nan'),True])
def test_invalid_coverage_threshold(value):
    with pytest.raises(ValueError):
        RoadMatcher(Net([]),minimum_coverage=value)


def test_exact_imported_chennai_geometries_retain_full_coverage():
    net = read_network()
    matcher = RoadMatcher(net)
    checked = 0
    for edge in net.getEdges():
        if not edge.allows('passenger') or edge.getLength() < 15:
            continue
        row = observation(road_geometry=tuple(net.convertXY2LonLat(*p) for p in edge.getShape()))
        result = matcher.match(row)
        assert result.matching_status == 'MATCHED', (edge.getID(),result.match_reason)
        assert result.matched_sumo_edges == (edge.getID(),)
        assert result.matching_coverage == pytest.approx(1,abs=1e-8)
        checked += 1
    assert checked == 744
