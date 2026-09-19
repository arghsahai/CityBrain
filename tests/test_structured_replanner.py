from copy import deepcopy

import pytest

from citybrain.models.plan import EmergencyPlan
from citybrain.models.planner_result import PlannerOutcome
from citybrain.planner.replanner import Replanner
from citybrain.planner.replanning_policy import ReplanningPolicy


def plan(route=("a",), revision=0, plan_id="incident-P0"):
    return EmergencyPlan(
        "ambulance", "hospital", list(route), 10,
        plan_id=plan_id, emergency_id="incident", status="ACTIVE",
        revision=revision,
    )


def roads(**times):
    return {
        edge: {"travel_time": value, "congestion": "LOW", "to": f"j-{edge}"}
        for edge, value in times.items()
    }


def test_legacy_replan_mutates_and_returns_same_plan():
    current = plan()
    state = {"roads": roads(a=20, b=10), "routes": {"old": ["a"], "new": ["b"]}}
    result = Replanner().replan(current, state)
    assert result is current and current.route == ["b"] and current.eta == 10


def test_structured_proposal_does_not_mutate_current_plan():
    current = plan()
    before = deepcopy(current)
    state = {"roads": roads(a=20, b=10), "routes": {"new": ["b"]}}
    proposal = Replanner().propose(current, state, current_time=5)
    assert current == before
    assert proposal.proposed_plan.route == ["b"]
    assert proposal.proposed_plan.plan_id == "incident-P1"
    assert proposal.proposed_plan.parent_plan_id == "incident-P0"
    assert proposal.proposed_plan.signal_priority == ["j-b"]


def test_structured_replan_exposes_audit_fields():
    current = plan()
    state = {"roads": roads(a=20, b=10), "routes": {"old": ["a"], "new": ["b"]}}
    result = Replanner(policy=ReplanningPolicy(minimum_improvement=5)).replan_structured(
        current, state, current_time=20, active_since=0,
    )
    assert result.decision is PlannerOutcome.REPLAN
    assert result.current_plan_id == "incident-P0"
    assert result.current_route == ["a"] and result.remaining_route == ["a"]
    assert set(result.candidate_routes) == {"old", "new"}
    assert result.improvement == 10 and result.threshold == 5
    assert result.validation_result.valid
    assert result.proposed_plan_id == "incident-P1"


def test_structured_replan_uses_remaining_route_not_history():
    current = plan(("past", "future"))
    state = {
        "roads": {
            "past": {"travel_time": 10, "blocked": True},
            "future": {"travel_time": 10},
        },
        "routes": {"remaining": ["future"]},
    }
    result = Replanner().replan_structured(
        current, state, remaining_route=["future"],
    )
    assert result.validation_result.valid
    assert result.decision is PlannerOutcome.KEEP


def test_all_unusable_candidates_returns_no_route():
    current = plan()
    state = {
        "roads": {"a": {"travel_time": float("inf")}, "b": {"blocked": True, "travel_time": 2}},
        "routes": {"one": ["a"], "two": ["b"]},
    }
    result = Replanner().structured_replan(current, state)
    assert result.decision is PlannerOutcome.NO_ROUTE
    assert result.proposed_plan is None
    assert result.metadata["proposal_reason"] == "all_candidate_routes_unusable"


def test_accept_requires_a_replan_decision():
    current = plan()
    state = {"roads": roads(a=10), "routes": {"same": ["a"]}}
    result = Replanner().replan_structured(current, state)
    assert result.decision is PlannerOutcome.KEEP
    with pytest.raises(ValueError):
        Replanner().accept(result)


def test_successive_acceptance_replaces_active_plan_p0_p1_p2():
    replanner = Replanner()
    p0 = replanner.set_active_plan(plan(), accepted_time=0)

    state1 = {
        "roads": {
            "a": {"travel_time": 10, "blocked": True},
            "b": {"travel_time": 12, "to": "j-b"},
        },
        "routes": {"blocked": ["a"], "alternative": ["b"]},
    }
    decision1 = replanner.evaluate_active(state1, current_time=1)
    p1 = replanner.accept(decision1, accepted_time=1)
    assert p0.plan_id == "incident-P0"
    assert p1.plan_id == "incident-P1" and replanner.active_plan is p1

    state2 = {
        "roads": {
            "b": {"travel_time": 12, "blocked": True},
            "c": {"travel_time": 14, "to": "j-c"},
        },
        "routes": {"blocked": ["b"], "alternative": ["c"]},
    }
    decision2 = replanner.evaluate_active(state2, current_time=2)
    p2 = replanner.accept_plan(decision2, accepted_time=2)
    assert decision2.current_plan_id == "incident-P1"
    assert p2.plan_id == "incident-P2" and p2.parent_plan_id == "incident-P1"
    assert replanner.active_plan.route == ["c"]
