"""Deterministic observation sequences; real teammate planner/executor retained."""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from citybrain.chennai.stability import ChennaiRuntime, SoftRouteGuard, StabilityConfig, hard_invalidation
from citybrain.core.road_state import RoadState
from citybrain.core.vehicle_state import VehicleState
from citybrain.integration.routing import RouteValidation
from citybrain.models.emergency import Emergency
from citybrain.models.planner_result import PlannerOutcome
from citybrain.dashboard.server import reduce_events
from test_final_runtime import PhysicalInterface


@pytest.fixture
def runtime():
    r = ChennaiRuntime(MagicMock())
    r.core.traci = PhysicalInterface()
    r.core.city_state.simulation_time = 1
    r.core.city_state.vehicles['amb'] = VehicleState('amb','a','a_0',10,(0,0),['a','b','z'],0,vehicle_type='ambulance')
    for edge,cost in {'a':5,'b':10,'c':30,'z':5}.items():
        r.core.city_state.roads[edge] = RoadState(edge,1,10,100,10,1,0,cost,'LOW')
    def step(blocked_edges=None):
        r.core.city_state.simulation_time += 1
        return r.core.city_state, [], {}
    r.core.step = step
    result = r.create_emergency_plan(Emergency('EM','J0','HIGH','ROAD_ACCIDENT'))
    assert result.success
    return r


def evaluate(r, now, b=60, c=10, stopped=False):
    r.core.city_state.simulation_time = now
    r.core.city_state.roads['b'].travel_time = float('inf') if stopped else b
    r.core.city_state.roads['b'].average_speed = 0 if stopped else 10
    r.core.city_state.roads['c'].travel_time = c
    raw = r.evaluate_replan()
    return r.handle_replan_result(raw)


@pytest.mark.parametrize('description',['temporary stop','traffic-light queue','brief congestion spike'])
def test_transient_deterioration_does_not_change_route(runtime,description):
    initial = deepcopy(runtime.active_plan)
    first = evaluate(runtime,20,stopped=description!='brief congestion spike')
    assert first.decision is PlannerOutcome.KEEP
    second = evaluate(runtime,25,b=10,c=30)
    assert second.decision is PlannerOutcome.KEEP
    assert runtime.active_plan == initial
    assert runtime.core.traci.route == initial.route
    assert runtime.stability_guard.pending_route is None


@pytest.mark.parametrize('stopped',[False,True])
def test_persistent_congestion_and_sustained_alternative_execute(runtime,stopped):
    assert evaluate(runtime,20,stopped=stopped).decision is PlannerOutcome.KEEP
    assert evaluate(runtime,39,stopped=stopped).decision is PlannerOutcome.KEEP
    result = evaluate(runtime,40,stopped=stopped)
    assert result.decision is PlannerOutcome.REPLAN
    assert runtime.active_plan.route == ['a','c','z'] == runtime.core.traci.route
    assert runtime.active_plan.revision == 1
    actions = [e['action'] for e in runtime.runtime_evidence]
    assert actions.index('ROUTE_EXECUTION') < actions.index('REPLAN_ACCEPTED')
    execution = next(e['execution'] for e in runtime.runtime_evidence if e['action']=='ROUTE_EXECUTION')
    assert execution['verification'] == 'VERIFIED'
    assert runtime.replan_latencies == [20]
    assert runtime.stability_guard.pending_route is None


def test_alternating_candidates_restart_confirmation(runtime):
    assert evaluate(runtime,20).decision is PlannerOutcome.KEEP
    assert evaluate(runtime,29,b=10,c=30).decision is PlannerOutcome.KEEP
    assert evaluate(runtime,30).decision is PlannerOutcome.KEEP
    assert evaluate(runtime,49).decision is PlannerOutcome.KEEP
    assert runtime.active_plan.revision == 0
    assert evaluate(runtime,50).decision is PlannerOutcome.REPLAN


def test_soft_infinite_cost_cannot_bypass_commitment(runtime):
    runtime.stability_guard = SoftRouteGuard(StabilityConfig(0))
    result = evaluate(runtime,7,stopped=True)
    assert result.decision is PlannerOutcome.KEEP
    assert result.reason == 'soft_change_commitment_pending'
    assert result.commitment_satisfied is False
    assert runtime.active_plan.revision == 0
    assert evaluate(runtime,11,stopped=True).decision is PlannerOutcome.REPLAN


def test_explicit_blockage_keeps_immediate_override(runtime):
    runtime.core.city_state.roads['b'].blocked = True
    result = evaluate(runtime,7)
    assert result.decision is PlannerOutcome.REPLAN
    assert runtime.active_plan.revision == 1
    assert runtime.core.traci.route == ['a','c','z']
    event = next(e for e in runtime.runtime_evidence if e['action']=='STABILITY_DECISION')
    assert event['stability']['outcome'] == 'HARD_FAILURE_BYPASS'
    assert runtime.replan_latencies == [0]


def test_soft_invalid_override_cannot_bypass_cooldown(runtime):
    runtime.config = replace(runtime.config,minimum_commitment=1)
    runtime.stability_guard = SoftRouteGuard(StabilityConfig(0))
    assert evaluate(runtime,20).decision is PlannerOutcome.REPLAN
    runtime.core.city_state.simulation_time = 22
    runtime.core.city_state.roads['b'].travel_time = 10
    runtime.core.city_state.roads['c'].travel_time = float('inf')
    runtime.core.city_state.roads['c'].average_speed = 0
    result = runtime.handle_replan_result(runtime.evaluate_replan())
    assert result.decision is PlannerOutcome.KEEP
    assert result.reason == 'soft_change_cooldown_pending'
    assert result.cooldown_satisfied is False
    assert runtime.active_plan.revision == 1


def test_physical_disconnection_bypasses_guard(runtime):
    # Existing policy may propose a valid alternative even with finite old costs.
    runtime.core.traci.links['b'] = set()
    result = evaluate(runtime,20)
    assert result.decision is PlannerOutcome.REPLAN
    assert runtime.core.traci.route == ['a','c','z']
    event = next(e for e in runtime.runtime_evidence if e['action']=='STABILITY_DECISION')
    assert event['stability']['hard_reason'] == 'physical_route_invalid:disconnected_route'


def test_unreachable_hospital_is_immediate_no_route(runtime):
    runtime.core.city_state.roads['z'].blocked = True
    runtime.core.city_state.roads['z'].travel_time = float('inf')
    result = evaluate(runtime,7)
    assert result.decision is PlannerOutcome.NO_ROUTE
    assert runtime.terminal_outcome == 'NO_ROUTE'
    assert runtime.active_plan is None
    assert runtime.arrival_time is None
    assert runtime.stability_guard.pending_route is None
    assert 'amb' not in runtime.core.reserved_ambulances


def test_confirmation_survives_progress_along_common_prefix(runtime):
    evaluate(runtime,20)
    runtime.core.traci.route = ['a','b','z']
    runtime.core.traci.index = 1
    runtime.core.traci.edge = 'b'
    # Direct guard sequence isolates common-prefix progress without inventing an
    # alternative after a physical branch has already been passed.
    result = runtime.evaluate_replan()
    guard = SoftRouteGuard()
    args = dict(active_since=1,last_replan_time=None,minimum_commitment=10,cooldown=5)
    proposal = replace(result,decision=PlannerOutcome.REPLAN,
        proposed_plan=replace(runtime.active_plan,route=['a','b','z']))
    guard.consider(proposal,now=20,**args)
    proposal = replace(proposal,proposed_plan=replace(proposal.proposed_plan,route=['b','z']))
    effective, details = guard.consider(proposal,now=40,**args)
    assert effective.decision is PlannerOutcome.REPLAN
    assert details['pending_since'] == 20


def test_failed_execution_keeps_accepted_plan(runtime):
    evaluate(runtime,20)
    previous = deepcopy(runtime.active_plan)
    runtime.core.traci.fail = True
    result = evaluate(runtime,40)
    assert result.accepted_plan is None
    assert runtime.active_plan == previous == runtime.replanner.active_plan
    assert runtime.core.traci.route == previous.route
    assert runtime.terminal_outcome is None


def test_readback_failure_cannot_accept_proposal(runtime):
    evaluate(runtime,20)
    runtime.core.traci.extra_once = True
    previous = deepcopy(runtime.active_plan)
    result = evaluate(runtime,40)
    assert result.accepted_plan is None
    assert runtime.active_plan == previous
    assert runtime.core.traci.route == previous.route


@pytest.mark.parametrize('outcome',['NO_ROUTE','TIMEOUT','TELEPORTED','ERROR','EXECUTION_FAILED'])
def test_terminal_cleanup_never_creates_arrival(runtime,outcome):
    evaluate(runtime,20)
    assert runtime.stability_guard.pending_route
    runtime._finalize(outcome,'injected terminal observation')
    assert runtime.stability_guard.pending_route is None
    assert runtime.active_plan is None and runtime.replanner.active_plan is None
    assert runtime.core.get_active_route('amb') is None
    assert 'amb' not in runtime.core.reserved_ambulances
    assert runtime.arrival_time is None


def test_teleport_observation_still_terminates_without_arrival(runtime):
    evaluate(runtime,20)
    runtime.core.city_state.terminal_vehicles['amb'] = 'TELEPORTED'
    runtime.step()
    assert runtime.terminal_outcome == 'TELEPORTED'
    assert runtime.arrival_time is None
    assert runtime.stability_guard.pending_route is None


def test_false_arrival_is_rejected_by_existing_runtime(runtime):
    runtime.core.city_state.terminal_vehicles['amb'] = 'ARRIVED'
    runtime.step()
    assert runtime.terminal_outcome == 'FAILED_BLOCKED'
    assert runtime.arrival_time is None


def test_verified_hospital_arrival_clears_guard(runtime):
    evaluate(runtime,20)
    vehicle = runtime.core.city_state.vehicles['amb']
    vehicle.edge_id = 'z'
    vehicle.route_index = 2
    runtime.core.city_state.terminal_vehicles['amb'] = 'ARRIVED'
    runtime.step()
    assert runtime.terminal_outcome == 'SUCCESS'
    assert runtime.arrival_time == 21
    assert runtime.stability_guard.pending_route is None
    assert runtime.core.get_active_route('amb') is None


def test_guard_exception_uses_existing_exception_cleanup(runtime):
    runtime.core.city_state.simulation_time = 20
    runtime.core.city_state.roads['b'].travel_time = 60
    runtime.core.city_state.roads['c'].travel_time = 10
    def fail(*args,**kwargs):
        raise RuntimeError('injected guard failure')
    runtime.stability_guard.consider = fail
    runtime.step()
    assert runtime.terminal_outcome == 'ERROR'
    assert runtime.active_plan is None
    assert runtime.core.get_active_route('amb') is None
    assert 'amb' not in runtime.core.reserved_ambulances


def test_evidence_failure_does_not_prevent_confirmed_acceptance(runtime):
    from test_evidence_safety import FailingWriter
    runtime.writer = FailingWriter({'STABILITY_DECISION'})
    evaluate(runtime,20)
    evaluate(runtime,40)
    assert runtime.active_plan.revision == 1
    assert runtime.core.traci.route == runtime.active_plan.route
    assert runtime.evidence_failures


def test_stability_keep_is_the_dashboard_decision(runtime):
    evaluate(runtime,20)
    state = reduce_events(runtime.runtime_evidence)
    assert state['decision']['decision'] == 'KEEP'
    assert state['decision']['reason'] == 'soft_change_confirmation_pending'
    assert state['plan']['revision'] == 0
    assert any(e['action']=='KEEP' for e in state['timeline'])


def test_compact_guard_record_keeps_decision_without_repeating_observation(runtime):
    from citybrain.chennai.telemetry import compact_event
    evaluate(runtime,20)
    raw = runtime.runtime_evidence[-1]
    assert raw['action']=='STABILITY_DECISION' and raw['context']
    compact = compact_event(raw)
    assert 'context' not in compact and 'active_plan' not in compact
    assert compact['planner_result']['decision']=='KEEP'
    assert raw['context']
    state = reduce_events([compact_event(e) for e in runtime.runtime_evidence])
    assert state['decision']['decision']=='KEEP'
    assert state['plan']['revision']==0
    assert state['position']['edge']=='a'


@pytest.mark.parametrize('value',[-1,float('inf'),float('nan'),True])
def test_configuration_rejects_invalid_windows(value):
    with pytest.raises(ValueError):
        StabilityConfig(value)
