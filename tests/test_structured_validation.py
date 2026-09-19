import pytest

from citybrain.models.plan import EmergencyPlan
from citybrain.planner.plan_validator import PlanValidator


@pytest.fixture
def plan():
    return EmergencyPlan("a", "h", ["past", "current", "future"], 30)


def measured_state():
    return {"roads": {
        "past": {"travel_time": 10},
        "current": {"travel_time": 10},
        "future": {"travel_time": 10},
    }}


def test_valid_route_has_structured_reason(plan):
    result = PlanValidator().validate_structured(plan, measured_state())
    assert result.valid and result.reason == "remaining_route_valid"
    assert len(result.checked_components) == 3


def test_blocked_route_requires_replan(plan):
    state = measured_state()
    state["roads"]["future"]["blocked"] = True
    result = PlanValidator().validate_result(plan, state)
    assert not result.valid and result.replan_required
    assert result.reason == "blocked_edge" and result.invalidated_component == "future"


@pytest.mark.parametrize("road,reason", [
    (None, "missing_road_state"),
    ({}, "travel_time_unavailable"),
    ({"travel_time": float("inf")}, "unreachable_edge"),
    ({"travel_time": -1}, "invalid_travel_time"),
])
def test_unusable_road_state_is_explicit(plan, road, reason):
    state = measured_state()
    if road is None:
        del state["roads"]["future"]
    else:
        state["roads"]["future"] = road
    result = PlanValidator().validate_structured(plan, state)
    assert not result.valid and result.reason == reason


def test_only_remaining_route_is_validated(plan):
    state = measured_state()
    state["roads"]["past"]["blocked"] = True
    result = PlanValidator().validate_structured(
        plan, state, remaining_route=["current", "future"],
    )
    assert result.valid and result.remaining_route == ["current", "future"]


def test_assigned_unavailable_ambulance_does_not_invalidate_route(plan):
    state = measured_state()
    state["ambulances"] = [{"id": "a", "available": False}]
    assert PlanValidator().validate_structured(plan, state).valid


def test_boolean_api_tolerates_legacy_measurement_free_roads(plan):
    state = {"roads": {edge: {"blocked": False} for edge in plan.route}}
    validator = PlanValidator()
    assert validator.validate(plan, state) is True
    state["roads"]["future"]["blocked"] = True
    assert validator.validate(plan, state) is False
