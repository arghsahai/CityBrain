"""Real planner/runtime contracts with a deterministic physical-interface double."""
from copy import deepcopy
from pathlib import Path
import json
from unittest.mock import MagicMock
import pytest

from citybrain.main import CityBrainRuntime, RuntimeConfig
from citybrain.core.road_state import RoadState
from citybrain.core.vehicle_state import VehicleState
from citybrain.core.route_executor import RouteAction, RouteExecutor
from citybrain.core.state_refresh import refresh_city_state
from citybrain.events import EventType, CityBrainEvent
from citybrain.integration.routing import validate_route, normalize_candidates
from citybrain.models.emergency import Emergency
from citybrain.models.planner_result import PlannerOutcome


class PhysicalInterface:
    def __init__(self):
        self.route = ['a', 'b', 'z']; self.index = 0; self.edge = 'a'
        self.fail = False; self.calls = []; self.extra_once = False
        self.links = {'a': {'b', 'c'}, 'b': {'z'}, 'c': {'z'}, 'z': set()}
        self.topology = {'a': {'from': 'J0', 'to': 'J1'}, 'b': {'from': 'J1', 'to': 'J2'},
                         'c': {'from': 'J1', 'to': 'J2'}, 'z': {'from': 'J2', 'to': 'J9'}}

    def vehicle_exists(self, vehicle): return True
    def edge_usable(self, edge, vehicle): return edge in self.links
    def successors(self, edge, vehicle): return set(self.links.get(edge, set()))
    def edge_topology(self, edge): return self.topology[edge]
    def route_position(self, vehicle):
        return dict(edge=self.edge, route_index=self.index, route=list(self.route),
                    remaining_route=list(self.route[self.index:]))
    def apply_route(self, vehicle, route):
        self.calls.append(list(route))
        if self.fail: raise RuntimeError('injected execution failure')
        self.route = self.route[:self.index] + list(route)
        if self.extra_once:
            self.route.append('wrong_destination'); self.extra_once = False
    def current_route_suffix(self, vehicle): return self.route[self.index:]


@pytest.fixture
def runtime():
    r = CityBrainRuntime(MagicMock())
    interface = PhysicalInterface(); r.core.traci = interface
    r.core.city_state.simulation_time = 1
    r.core.city_state.vehicles['amb'] = VehicleState('amb', 'a', 'a_0', 10, (0, 0),
                                                    ['a', 'b', 'z'], 0, vehicle_type='ambulance')
    for edge, cost in {'a': 5, 'b': 10, 'c': 30, 'z': 5}.items():
        r.core.city_state.roads[edge] = RoadState(edge, 1, 10, 100, 10, 1, 0, cost, 'LOW')
    def step(blocked_edges=None):
        r.core.city_state.simulation_time += 1
        return r.core.city_state, [], {}
    r.core.step = step
    return r


def dispatch(r):
    result = r.create_emergency_plan(Emergency('EM', 'J0', 'HIGH', 'ROAD_ACCIDENT'))
    assert result.success
    return result


def improve(r, now=20):
    r.core.city_state.simulation_time = now
    r.core.city_state.roads['b'].travel_time = 60
    r.core.city_state.roads['c'].travel_time = 10
    return r.evaluate_replan()


def test_p0_execution_failure_never_becomes_active(runtime):
    runtime.core.traci.fail = True
    result = runtime.create_emergency_plan(Emergency('EM', 'J0', 'HIGH', 'MEDICAL'))
    assert not result.success
    assert runtime.active_plan is None and runtime.replanner.active_plan is None
    assert runtime.plan_history == [] and runtime.core.get_active_route('amb') is None
    assert runtime.terminal_outcome == 'EXECUTION_FAILED'


@pytest.mark.parametrize('failed_revision', [1, 2])
def test_failed_replan_preserves_previous_logical_and_physical_plan(runtime, failed_revision):
    dispatch(runtime)
    first = improve(runtime)
    if failed_revision == 2:
        runtime.handle_replan_result(first)
        runtime.core.city_state.simulation_time = 40
        runtime.core.city_state.roads['b'].travel_time = 5
        runtime.core.city_state.roads['c'].travel_time = 60
    result = runtime.evaluate_replan()
    previous = deepcopy(runtime.active_plan)
    physical = list(runtime.core.traci.route)
    runtime.core.traci.fail = True
    runtime.handle_replan_result(result)
    assert result.accepted_plan is None
    assert runtime.active_plan == previous == runtime.replanner.active_plan
    assert runtime.core.traci.route == physical
    assert runtime.core.get_active_route('amb') == previous.route
    assert runtime.terminal_outcome is None


def test_physical_verification_precedes_acceptance(runtime):
    dispatch(runtime); result = improve(runtime)
    original = runtime.replanner.accept
    def accept(proposal, **kwargs):
        assert runtime.core.traci.route == proposal.proposed_plan.route
        assert runtime.runtime_evidence[-1]['execution']['verification'] == 'VERIFIED'
        assert runtime.active_plan.revision == 0
        return original(proposal, **kwargs)
    runtime.replanner.accept = accept
    runtime.handle_replan_result(result)
    assert runtime.active_plan.revision == 1
    assert result.accepted_plan == runtime.active_plan == runtime.replanner.active_plan


def test_extra_destination_suffix_rejected_and_previous_route_restored():
    interface = PhysicalInterface(); interface.extra_once = True
    result = RouteExecutor().execute(interface, RouteAction('amb', ['a', 'c', 'z']))
    assert not result.success and result.verification == 'SUFFIX_MISMATCH'
    assert result.rollback_verified and result.safe_to_continue
    assert interface.route == ['a', 'b', 'z']


@pytest.mark.parametrize('observed', [['a'], ['b'], ['a', 'b', 'wrong'], ['prefix', 'a', 'b']])
def test_suffix_requires_exact_equality(observed):
    assert RouteExecutor._verify_suffix(['a', 'b'], observed) != 'VERIFIED'


def test_current_position_normalization_and_travelled_prefix(runtime):
    interface = runtime.core.traci; interface.index = 1; interface.edge = 'b'
    candidates, rejected = normalize_candidates(interface, 'amb',
        {'good': ['a', 'b', 'z'], 'behind': ['a', 'c', 'z'], 'disconnected': ['b', 'a', 'z']},
        {'id': 'H1', 'location': 'J9'}, interface.route_position('amb'))
    assert candidates == {'good': ['b', 'z']}
    assert rejected['disconnected'] == 'disconnected_route'
    executed = RouteExecutor().execute(interface, RouteAction('amb', ['b', 'z']))
    assert executed.success and executed.observed_route == ['a', 'b', 'z']
    assert executed.observed_suffix == ['b', 'z']


@pytest.mark.parametrize('route,reason', [(['a', 'z'], 'disconnected_route'),
    (['b', 'z'], 'route_does_not_start_at_current_edge'), (['a', 'b'], 'hospital_endpoint_mismatch')])
def test_invalid_physical_routes(runtime, route, reason):
    result = validate_route(runtime.core.traci, 'amb', route, {'id': 'H1', 'location': 'J9'})
    assert not result.valid and result.reason == reason


def test_hospital_metadata_missing_is_configuration_failure(runtime):
    runtime.hospitals = [{'id': 'H1', 'icu_available': True}]
    result = runtime.create_emergency_plan(Emergency('EM', 'J0', 'HIGH', 'MEDICAL'))
    assert not result.success and runtime.terminal_outcome == 'ERROR'
    assert not runtime.core.traci.calls


def test_internal_edge_defers_then_retries(runtime):
    dispatch(runtime); runtime.core.traci.edge = ':junction'
    assert improve(runtime) is None
    assert len(runtime.core.traci.calls) == 1 and runtime._deferred
    runtime.core.traci.edge = 'a'
    runtime.step()
    assert runtime.active_plan.revision == 1 and not runtime._deferred


@pytest.mark.parametrize('event', [EventType.ROAD_BLOCKED, EventType.ROAD_UNBLOCKED,
                                  EventType.CONGESTION_CHANGED, EventType.ROUTE_INVALIDATED])
def test_meaningful_events_trigger_evaluation(runtime, event):
    dispatch(runtime)
    runtime._last_evaluation = runtime.now
    runtime.config = RuntimeConfig(reevaluation_interval=100)
    def step(**kwargs): return runtime.core.city_state, [CityBrainEvent(event, runtime.now)], {}
    runtime.core.step = step
    runtime.step()
    assert any(e['action'] == 'DECISION' for e in runtime.runtime_evidence)


def test_periodic_evaluation_without_events(runtime):
    dispatch(runtime); runtime.step()
    assert any(e['action'] == 'DECISION' for e in runtime.runtime_evidence)


def test_minimum_improvement_keeps_plan(runtime):
    dispatch(runtime); runtime.core.city_state.simulation_time = 20
    runtime.core.city_state.roads['c'].travel_time = 9
    decision = runtime.evaluate_replan()
    assert decision.decision is PlannerOutcome.KEEP and decision.reason == 'improvement_below_threshold'


def test_commitment_and_cooldown_and_blocked_override(runtime):
    from citybrain.planner.replanning_policy import ReplanningPolicy
    dispatch(runtime)
    assert improve(runtime, 2).reason == 'minimum_commitment_not_elapsed'
    runtime.replanner.policy = ReplanningPolicy(minimum_improvement=5, minimum_commitment=2, cooldown=20)
    runtime.replanner.last_replan_time = 1
    assert improve(runtime, 5).reason == 'cooldown_not_elapsed'
    runtime.core.city_state.roads['b'].blocked = True
    assert runtime.evaluate_replan().decision is PlannerOutcome.REPLAN


@pytest.mark.parametrize('outcome', ['TELEPORTED', 'DISAPPEARED'])
def test_terminal_failure_clears_plan_and_stops_replanning(runtime, outcome):
    dispatch(runtime); runtime.core.city_state.terminal_vehicles['amb'] = outcome
    runtime.step()
    assert runtime.terminal_outcome == ('TELEPORTED' if outcome == 'TELEPORTED' else 'FAILED_BLOCKED')
    assert runtime.active_plan is None and runtime.replanner.active_plan is None
    count = len(runtime.runtime_evidence)
    runtime.core.city_state.terminal_vehicles['amb'] = 'ARRIVED'; runtime.step()
    assert len(runtime.runtime_evidence) == count and runtime.terminal_outcome != 'SUCCESS'


@pytest.mark.parametrize('correct', [True, False])
def test_hospital_arrival_requires_last_physical_edge(runtime, correct):
    dispatch(runtime)
    v = runtime.core.city_state.vehicles['amb']
    v.edge_id = 'z' if correct else 'b'; v.route_index = 2 if correct else 1
    runtime.core.city_state.terminal_vehicles['amb'] = 'ARRIVED'
    runtime.step()
    assert runtime.terminal_outcome == ('SUCCESS' if correct else 'FAILED_BLOCKED')
    assert (runtime.arrival_time is not None) == correct
    assert runtime.active_plan is None and runtime.replanner.active_plan is None


def test_empty_candidates_no_route_without_actions(runtime):
    runtime.routes = {}; result = runtime.create_emergency_plan(Emergency('EM', 'J0', 'HIGH', 'MEDICAL'))
    assert result.outcome is PlannerOutcome.NO_ROUTE and runtime.terminal_outcome == 'NO_ROUTE'
    assert runtime.core.traci.calls == []


def test_blocked_cut_terminal_no_route(runtime):
    dispatch(runtime)
    runtime.core.city_state.roads['b'].blocked = runtime.core.city_state.roads['c'].blocked = True
    runtime.evaluate_replan()
    assert runtime.terminal_outcome == 'NO_ROUTE' and len(runtime.core.traci.calls) == 1


def test_transient_infinite_cost_waits_without_false_unreachable(runtime):
    dispatch(runtime)
    runtime.core.city_state.roads['b'].travel_time = runtime.core.city_state.roads['c'].travel_time = float('inf')
    runtime.evaluate_replan()
    assert runtime.terminal_outcome is None
    assert runtime.runtime_evidence[-1]['action'] == 'NO_ROUTE_WAIT'


def test_advisories_recorded_without_physical_signal_actions(runtime):
    dispatch(runtime)
    event = next(e for e in runtime.runtime_evidence if e['action'] == 'SIGNAL_ADVISORIES')
    assert event['recommendations'] and event['execution_attempted'] is False
    assert all(r['advisory'] and not r['executed'] for r in event['advisory_results'])


def test_evidence_persisted_as_immutable_strict_json(runtime, tmp_path):
    from citybrain.integration.evidence import EvidenceWriter
    runtime.writer = EvidenceWriter(tmp_path/'evidence')
    dispatch(runtime); old = deepcopy(runtime.runtime_evidence)
    runtime.handle_replan_result(improve(runtime)); runtime._finalize('TIMEOUT', 'test_end')
    events = [json.loads(line) for line in runtime.writer.events.read_text().splitlines()]
    summary = json.loads((runtime.writer.directory/'summary.json').read_text())
    assert summary['terminal_outcome'] == 'TIMEOUT' and summary['travel_time'] is None
    assert any(e['action'] == 'REPLAN_ACCEPTED' and e['accepted_revision'] == 1 for e in events)
    assert old == runtime.runtime_evidence[:len(old)]
    with pytest.raises(FileExistsError): EvidenceWriter(runtime.writer.directory)
    with pytest.raises(ValueError): EvidenceWriter(Path('experiments/results/new-integration'))


def test_live_progress_only_invalidates_remaining_route():
    from test_citybrain_core import _build_traci_mock
    from citybrain.core.citybrain_core import CityBrainCore
    raw = _build_traci_mock(); raw.vehicle.getIDList.return_value = ('amb',)
    raw.edge.getIDList.return_value = ('E1', 'E2', 'E3')
    core = CityBrainCore(raw); core.refresh_state(blocked_edges=[])
    core.set_active_route('amb', ['E1', 'E2', 'E3'])
    raw.vehicle.getRouteIndex.return_value = 1; raw.vehicle.getRoadID.return_value = 'E2'
    _, events, _ = core.refresh_state_with_events(blocked_edges=['E1'])
    assert core.get_active_route('amb') == ['E2', 'E3']
    assert not any(e.event_type is EventType.ROUTE_INVALIDATED for e in events)
    _, events, _ = core.refresh_state_with_events(blocked_edges=['E3'])
    assert any(e.event_type is EventType.ROUTE_INVALIDATED for e in events)


def test_core_teleport_latched_across_reinsertion_and_arrival():
    from test_citybrain_core import _build_traci_mock
    from citybrain.core.city_state import CityState
    raw = _build_traci_mock(); state = CityState()
    raw.vehicle.getIDList.return_value = ('amb',)
    refresh_city_state(raw, state, blocked_edges=[])
    # Teleport may be reported while SUMO still exposes the ID as active.
    raw.simulation.getStartingTeleportIDList.return_value = ('amb',)
    _, removals = refresh_city_state(raw, state, blocked_edges=[])
    assert removals == {'amb': 'TELEPORTED'}
    raw.simulation.getStartingTeleportIDList.return_value = ()
    refresh_city_state(raw, state, blocked_edges=[])
    raw.vehicle.getIDList.return_value = ()
    raw.simulation.getArrivedIDList.return_value = ('amb',)
    _, removals = refresh_city_state(raw, state, blocked_edges=[])
    assert state.terminal_vehicles['amb'] == 'TELEPORTED'
    assert 'ARRIVED' not in removals.values()


def test_reserved_or_teleported_ambulance_not_available(runtime):
    runtime.core.reserved_ambulances.add('amb')
    assert not runtime._resources()[0]['available']
    runtime.core.city_state.terminal_vehicles['amb'] = 'TELEPORTED'
    assert runtime._resources() == []


def test_timeout_finalizes_pending_emergency(runtime):
    dispatch(runtime)
    runtime.core.city_state.simulation_time = runtime.config.horizon
    runtime.step()
    assert runtime.terminal_outcome == 'TIMEOUT' and runtime.active_plan is None


def test_catalog_fallback_discovers_connected_alternative_without_forcing_replans(runtime):
    runtime.routes = {'catalog': ['a', 'b', 'z']}
    runtime.config = RuntimeConfig(topology_fallback=True)
    dispatch(runtime)
    runtime.core.city_state.roads['b'].blocked = True
    result = runtime.evaluate_replan()
    assert result.decision is PlannerOutcome.REPLAN
    assert result.proposed_plan.route == ['a', 'c', 'z']
    runtime.handle_replan_result(result)
    assert runtime.active_plan.revision == 1
    assert runtime.evaluate_replan().decision is PlannerOutcome.KEEP


def test_explicit_empty_catalog_never_uses_topology_fallback(runtime):
    runtime.routes = {}; runtime.config = RuntimeConfig(topology_fallback=True)
    result = runtime.create_emergency_plan(Emergency('EM', 'J0', 'HIGH', 'MEDICAL'))
    assert result.outcome is PlannerOutcome.NO_ROUTE and not runtime.core.traci.calls


def test_correct_goal_is_required_even_with_explicit_destination_edge(runtime):
    goal = {'id': 'H1', 'destination_edge': 'b', 'destination_junction': 'J9'}
    assert not validate_route(runtime.core.traci, 'amb', ['a', 'b'], goal).valid


def test_irrecoverable_physical_mismatch_is_terminal_execution_failure(runtime):
    dispatch(runtime); result = improve(runtime)
    from citybrain.core.route_executor import RouteResult
    runtime.core.execute_route = lambda *args, **kwargs: RouteResult(
        False, 'amb', result.proposed_plan.route, safe_to_continue=False,
        verification='READBACK_FAILED', reason='lost physical state')
    runtime.handle_replan_result(result)
    assert result.accepted_plan is None and runtime.terminal_outcome == 'EXECUTION_FAILED'
    assert runtime.plan_history[-1].revision == 0


@pytest.mark.parametrize('field,value', [('minimum_improvement',0),('cooldown',float('nan')),
                                       ('reevaluation_interval',-1),('candidate_limit',0)])
def test_runtime_configuration_rejects_unstable_or_invalid_values(field, value):
    with pytest.raises(ValueError): RuntimeConfig(**{field: value})


def test_uncommanded_physical_route_change_stops_with_failure(runtime):
    dispatch(runtime)
    runtime.core.traci.route = ['a', 'c', 'z']
    runtime.step()
    assert runtime.terminal_outcome == 'EXECUTION_FAILED'
    assert runtime.terminal_reason == 'uncommanded_physical_route_change'
    assert len(runtime.plan_history) == 1


def test_stale_replan_result_is_not_executed(runtime):
    dispatch(runtime); result = improve(runtime)
    runtime.handle_replan_result(result)
    calls = len(runtime.core.traci.calls)
    runtime.handle_replan_result(result)
    assert len(runtime.core.traci.calls) == calls and runtime.active_plan.revision == 1


def test_failed_start_writes_error_summary(tmp_path):
    from citybrain.main import run
    runtime = run(tmp_path/'missing.sumocfg', output=tmp_path/'output')
    assert runtime.terminal_outcome == 'ERROR'
    assert json.loads((tmp_path/'output/summary.json').read_text())['terminal_outcome'] == 'ERROR'
