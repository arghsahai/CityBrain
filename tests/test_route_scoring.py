from copy import deepcopy
import pytest
from citybrain.planner.route_scorer import RouteScorer


def score(road):
    return RouteScorer().explain_score(["e"], {"roads": {"e": road}})


@pytest.mark.parametrize("congestion,penalty", [("LOW", 0), ("MEDIUM", 5), ("HIGH", 15),
                                                ("NO_TRAFFIC", 0), ("UNKNOWN", 0), (None, 0)])
def test_positive_cost_and_congestion(congestion, penalty):
    result = score(dict(travel_time=10, congestion=congestion))
    assert result.usable and result.final_score == 10 + penalty
    assert result.base_travel_time == 10
    assert result.components[0]["congestion"] == congestion
    if congestion in (None, "UNKNOWN"):
        assert result.components[0]["reason"] == "unknown_congestion_no_penalty"


@pytest.mark.parametrize("road,reason", [
    ({}, "travel_time_unavailable"),
    ({"travel_time": None}, "travel_time_unavailable"),
    ({"travel_time": -1}, "invalid_travel_time"),
    ({"travel_time": float("nan")}, "invalid_travel_time"),
    ({"travel_time": float("inf")}, "unreachable_edge"),
    ({"travel_time": "10"}, "invalid_travel_time"),
    ({"travel_time": True}, "invalid_travel_time"),
    ({"travel_time": 10, "blocked": True}, "blocked_edge"),
    ({"travel_time": 0}, "zero_time_without_physical_estimate"),
    ({"travel_time": 0, "congestion": "NO_TRAFFIC"}, "zero_time_without_physical_estimate"),
])
def test_unscorable_costs(road, reason):
    result = score(road)
    assert not result.usable and result.final_score == float("inf")
    assert result.reason == reason and result.invalidated_edge == "e"


def test_free_flow_estimate_preserves_source():
    road = dict(travel_time=0, congestion="NO_TRAFFIC", road_length=100, speed_limit=10)
    before = deepcopy(road)
    result = score(road)
    assert result.base_travel_time == 10 and road == before
    assert result.components[0]["cost_source"] == "free_flow_estimate"


@pytest.mark.parametrize("field,value", [("road_length", 0), ("speed_limit", -1),
                                          ("road_length", float("inf")), ("speed_limit", None)])
def test_no_invalid_fallback(field, value):
    road = dict(travel_time=0, congestion="NO_TRAFFIC", road_length=100, speed_limit=10)
    road[field] = value
    assert not score(road).usable


def test_missing_edge_empty_route_and_numeric_compatibility():
    scorer = RouteScorer()
    assert scorer.calculate_score(["missing"], {}) == float("inf")
    assert scorer.calculate_score([], {}) == float("inf")
    state = {"roads": {"e": {"travel_time": 10, "congestion": "MEDIUM"}}}
    assert scorer.calculate_score(["e"], state) == 15
    assert scorer.explain_score(["e"], state) == scorer.explain_score(["e"], state)
