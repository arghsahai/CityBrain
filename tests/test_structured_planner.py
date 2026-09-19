from copy import deepcopy

from citybrain.models.emergency import Emergency
from citybrain.models.planner_result import PlannerOutcome
from citybrain.planner.emergency_planner import EmergencyPlanner


def emergency():
    return Emergency("E-1", "j1", "HIGH", "ACCIDENT")


def state():
    return {
        "simulation_time": 12.0,
        "roads": {
            "slow": {"travel_time": 20, "congestion": "HIGH", "to": "j2"},
            "fast": {"travel_time": 10, "congestion": "LOW", "to": "j3"},
        },
        "routes": {"r-slow": ["slow"], "r-fast": ["fast"]},
        "ambulances": [{"id": "a1", "available": True}],
        "hospitals": [{"id": "h1", "icu_available": True}],
    }


def test_structured_planner_creates_auditable_plan():
    source = state()
    before = deepcopy(source)
    result = EmergencyPlanner().create_plan_result(emergency(), source)
    assert result.outcome is PlannerOutcome.PLAN_CREATED
    assert result.plan.plan_id == "E-1-P0"
    assert result.plan.route == ["fast"] and result.plan.eta == 10
    assert result.plan.created_time == 12.0 and result.plan.status == "PROPOSED"
    assert set(result.candidate_scores) == {"r-slow", "r-fast"}
    assert result.candidate_scores["r-fast"].components
    assert result.recommendations["signal"][0]["advisory"] is True
    assert result.recommendations["police"][0]["advisory"] is True
    assert source == before


def test_legacy_create_plan_returns_plan():
    plan = EmergencyPlanner().create_plan(emergency(), state())
    assert plan.route == ["fast"] and plan.ambulance_id == "a1"


def test_structured_planner_reports_no_ambulance():
    current = state()
    current["ambulances"] = []
    result = EmergencyPlanner().plan(emergency(), current)
    assert result.outcome is PlannerOutcome.NO_RESOURCE
    assert result.reason == "no_available_ambulance"


def test_structured_planner_reports_no_hospital():
    current = state()
    current["hospitals"] = []
    result = EmergencyPlanner().plan(emergency(), current)
    assert result.outcome is PlannerOutcome.NO_RESOURCE
    assert result.reason == "no_suitable_hospital"


def test_structured_planner_reports_no_candidate_routes():
    current = state()
    current["routes"] = {}
    result = EmergencyPlanner().plan(emergency(), current)
    assert result.outcome is PlannerOutcome.NO_ROUTE
    assert result.reason == "no_candidate_routes"


def test_structured_planner_reports_all_routes_unusable():
    current = state()
    current["roads"]["slow"]["blocked"] = True
    current["roads"]["fast"]["travel_time"] = float("inf")
    result = EmergencyPlanner().plan(emergency(), current)
    assert result.outcome is PlannerOutcome.NO_ROUTE
    assert result.reason == "all_candidate_routes_unusable"


def test_structured_planner_reports_invalid_input():
    result = EmergencyPlanner().plan(None, state())
    assert result.outcome is PlannerOutcome.INVALID_INPUT and result.plan is None
