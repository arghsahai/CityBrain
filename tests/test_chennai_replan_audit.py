"""Audit flags future suffix returns, not normal progress or a new diversion."""
import pytest
from tools.audit_chennai_replans import audit


def history(routes):
    events = []
    for revision, route in enumerate(routes):
        plan_id = f'P{revision}'
        if revision:
            events.append(dict(action='DECISION', simulation_time=revision*10,
                remaining_route=routes[revision-1], planner_result=dict(
                    proposed_plan={'plan_id': plan_id}, reason='material_improvement_and_timing_satisfied',
                    current_score=40, proposed_score=20, improvement=20, threshold=5)))
        events.append(dict(action='ROUTE_EXECUTION' if revision else 'INITIAL_EXECUTION', execution=dict(
            success=True,verification='VERIFIED',plan_id=plan_id,intended_suffix=route,observed_suffix=route)))
        events.append(dict(action='REPLAN_ACCEPTED' if revision else 'PLAN_ACCEPTED', simulation_time=revision*10,
            accepted_plan=dict(plan_id=plan_id,revision=revision,route=route)))
    return events


def test_flags_a_b_a_before_divergence():
    result = audit(history([['s','a','h'],['s','b','h'],['s','a','h']]))
    assert result['physically_verified_route_changes'] == 2
    assert result['stability_status'] == 'OSCILLATION_REVIEW_REQUIRED'
    assert result['repeated_future_suffix_returns'] == [dict(time=20,revision=2,earlier_revisions=[0])]


def test_new_diversion_is_not_a_return():
    result = audit(history([['s','a','h'],['s','b','h'],['s','c','h']]))
    assert result['repeated_future_suffix_returns'] == []


def test_return_comparison_is_suffix_aware():
    events = history([['old','s','a','h'],['s','b','h'],['s','a','h']])
    events[2]['remaining_route'] = ['s','a','h']
    result = audit(events)
    assert result['repeated_future_suffix_returns'][0]['earlier_revisions'] == [0]


def test_rejects_unverified_acceptance():
    events = history([['s','a','h']])
    events[0]['execution']['observed_suffix'] = ['s','unrelated','h']
    with pytest.raises(AssertionError):
        audit(events)
