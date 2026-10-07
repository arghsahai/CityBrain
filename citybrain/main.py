"""Single-emergency SUMO runtime: observe, propose, execute, verify, accept."""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import argparse
import json
import hashlib
import platform
import xml.etree.ElementTree as ET
import math
from pathlib import Path
import subprocess
import uuid

import sumolib
import traci

from citybrain.core.citybrain_core import CityBrainCore
from citybrain.events import EventType
from citybrain.integration.evidence import EvidenceWriter, snapshot
from citybrain.integration.routing import (destination_matches, generate_candidates,
    normalize_candidates, reachable_without_blocked, validate_destination, validate_route)
from citybrain.models.emergency import Emergency
from citybrain.models.planner_result import PlannerOutcome, PlanningResult
from citybrain.planner.emergency_planner import EmergencyPlanner
from citybrain.planner.replanner import Replanner
from citybrain.planner.replanning_policy import ReplanningPolicy

# Demonstration resource metadata, not a hospital inferred from a route score.
DEFAULT_HOSPITALS = [{'id': 'H1', 'destination_junction': 'J9', 'icu_available': True}]
TERMINAL_OUTCOMES = {'SUCCESS', 'NO_ROUTE', 'FAILED_BLOCKED', 'TELEPORTED',
                     'TIMEOUT', 'EXECUTION_FAILED', 'ERROR'}


@dataclass(frozen=True)
class RuntimeConfig:
    reevaluation_interval: float = 1.0
    minimum_improvement: float = 5.0
    minimum_commitment: float = 10.0
    cooldown: float = 5.0
    horizon: float = 900.0
    candidate_limit: int = 8
    topology_fallback: bool = False

    def __post_init__(self):
        for name in ('reevaluation_interval', 'minimum_improvement',
                     'minimum_commitment', 'cooldown', 'horizon'):
            value = getattr(self, name)
            if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
                raise ValueError(f'{name} must be positive and finite')
        if type(self.candidate_limit) is not int or self.candidate_limit < 1:
            raise ValueError('candidate_limit must be a positive integer')


class CityBrainRuntime:
    def __init__(self, traci_connection, routes=None, hospitals=None, *, config=None, output=None):
        self.core = CityBrainCore(traci_connection)
        # None enables topology candidates. Explicit {} deliberately supplies none.
        self.routes = deepcopy(routes)
        self.hospitals = deepcopy(DEFAULT_HOSPITALS if hospitals is None else hospitals)
        if routes is not None and not isinstance(routes, dict):
            raise ValueError('routes must be a mapping or None')
        if not isinstance(self.hospitals, list):
            raise ValueError('hospitals must be a list')
        self.config = config or RuntimeConfig()
        self.planner = EmergencyPlanner()
        self.replanner = Replanner(policy=ReplanningPolicy(
            minimum_improvement=self.config.minimum_improvement,
            minimum_commitment=self.config.minimum_commitment,
            cooldown=self.config.cooldown, invalid_route_override=True))
        self.active_plan = None
        self.emergency = None
        self.ambulance_id = None
        self.hospital = None
        self.plan_history = []
        self.runtime_evidence = []
        self.terminal_outcome = None
        self.terminal_reason = None
        self.dispatch_time = None
        self.arrival_time = None
        self.applied_replans = 0
        self.replan_latencies = []
        self._last_evaluation = -math.inf
        self._pending_candidate = None
        self._pending_since = None
        self._deferred = False
        self._last_context = {}
        self.provenance = {}
        self.writer = EvidenceWriter(output) if output is not None else None
        self._record_evidence('RUNTIME_CONFIG', configuration=self.config,
                              hospitals=self.hospitals, candidate_source='topology' if routes is None else 'explicit')

    @property
    def now(self):
        return self.core.city_state.simulation_time

    def _resources(self):
        return [{'id': v.vehicle_id, 'edge': v.edge_id, 'speed': v.speed,
                 'available': v.vehicle_id not in self.core.reserved_ambulances}
                for v in sorted(self.core.city_state.vehicles.values(), key=lambda v: v.vehicle_id)
                if v.vehicle_type == 'ambulance' and v.vehicle_id not in self.core.city_state.terminal_vehicles]

    def _context(self):
        position = self.core.traci.route_position(self.ambulance_id)
        self._last_context = {'physical_position': position}
        if position['edge'].startswith(':'):
            self._deferred = True
            self._record_evidence('DEFERRED', reason='internal_junction')
            return None
        self._deferred = False
        if self.active_plan is not None:
            accepted = self.active_plan.route
            edge = position['edge']
            expected = accepted[accepted.index(edge):] if edge in accepted else None
            if expected != position['remaining_route']:
                self._finalize('EXECUTION_FAILED', 'uncommanded_physical_route_change')
                return None
        state = self.core.build_planner_state(routes={}, hospitals=[self.hospital],
            ambulances=[{'id': self.ambulance_id, 'edge': position['edge'], 'available': True}])
        if self.routes is None:
            candidates, truncated = generate_candidates(self.core.traci, self.ambulance_id,
                state['roads'], self.hospital, position, self.config.candidate_limit)
            rejected = {}
        else:
            candidates, rejected = normalize_candidates(self.core.traci, self.ambulance_id,
                self.routes, self.hospital, position)
            truncated = False
            # An explicit, opt-in fallback preserves a supplied catalogue until
            # all its remaining routes are unusable. Empty {} never expands.
            usable = any(all(not state['roads'][e].get('blocked') and
                             math.isfinite(state['roads'][e]['travel_time']) and
                             state['roads'][e]['travel_time'] > 0 for e in route)
                         for route in candidates.values())
            if self.routes and self.config.topology_fallback and not usable:
                candidates, truncated = generate_candidates(self.core.traci, self.ambulance_id,
                    state['roads'], self.hospital, position, self.config.candidate_limit)
                self._last_context['topology_fallback_used'] = True
        state['routes'] = candidates
        self._last_context.update(planner_state=state, candidate_routes=candidates,
                                  rejected_candidates=rejected, search_truncated=truncated)
        return state, position

    def create_emergency_plan(self, emergency):
        if self.terminal_outcome or self.active_plan:
            return PlanningResult(PlannerOutcome.INVALID_INPUT, 'emergency_already_active_or_terminal')
        if self.emergency is not None and self.emergency.emergency_id != emergency.emergency_id:
            return PlanningResult(PlannerOutcome.INVALID_INPUT, 'single_emergency_runtime')
        self.emergency = emergency
        resources = self._resources()
        selected = self.planner.ambulance_agent.select(emergency, {'ambulances': resources})
        if not selected.success:
            self._record_evidence('WAITING_FOR_RESOURCE', reason=selected.reason)
            return PlanningResult(PlannerOutcome.NO_RESOURCE, selected.reason)
        self.ambulance_id = selected.selected['id']
        hospital = self.planner.hospital_agent.select(emergency, {'hospitals': self.hospitals})
        if not hospital.success or not validate_destination(hospital.selected):
            self._finalize('ERROR', 'hospital_destination_missing_or_unavailable')
            return PlanningResult(PlannerOutcome.INVALID_INPUT, self.terminal_reason)
        self.hospital = deepcopy(hospital.selected)
        try:
            context = self._context()
            if context is None:
                return PlanningResult(PlannerOutcome.NO_ROUTE, 'internal_junction_deferred')
            state, position = context
            self._last_evaluation = self.now
            result = self.planner.create_plan_result(emergency, state)
            self._record_evidence('INITIAL_DECISION', planner_result=result)
            if not result.success:
                if result.outcome is PlannerOutcome.NO_ROUTE:
                    self._handle_no_route(state, position)
                return result
            validation = validate_route(self.core.traci, result.plan.ambulance_id,
                                        result.plan.route, self.hospital, position)
            if not validation.valid:
                self._record_evidence('INITIAL_VALIDATION_FAILED', validation=validation)
                self._finalize('ERROR', validation.reason)
                return PlanningResult(PlannerOutcome.INVALID_INPUT, validation.reason)
            execution = self.core.execute_route(result.plan.ambulance_id, result.plan.route,
                                                result.plan.plan_id, hospital=self.hospital)
            self._record_evidence('INITIAL_EXECUTION', requested_action=result.plan.route,
                                  validation=validation, execution=execution)
            if not execution.success:
                if execution.verification == 'DEFERRED':
                    self._deferred = True
                else:
                    self._finalize('EXECUTION_FAILED', execution.reason)
                return PlanningResult(PlannerOutcome.INVALID_INPUT, execution.reason,
                                      metadata={'execution': snapshot(execution)})
            # This is the first logical acceptance point.
            self.active_plan = self.replanner.set_active_plan(result.plan, accepted_time=self.now)
            result.plan = self.active_plan
            self.dispatch_time = self.now
            self.core.reserved_ambulances.add(self.ambulance_id)
            self.plan_history.append(deepcopy(self.active_plan))
            self._record_evidence('PLAN_ACCEPTED', accepted_plan=self.active_plan,
                                  execution=execution, accepted_revision=0)
            self._record_advisories()
            return result
        except Exception as error:
            self._finalize('ERROR', f'{type(error).__name__}: {error}')
            return PlanningResult(PlannerOutcome.INVALID_INPUT, self.terminal_reason)

    def evaluate_replan(self):
        if self.active_plan is None or self.terminal_outcome:
            return None
        context = self._context()
        if context is None:
            return None
        state, position = context
        self._last_evaluation = self.now
        result = self.replanner.replan_structured(self.active_plan, state,
            remaining_route=position['remaining_route'], current_time=self.now)
        candidate = result.proposed_plan
        meaningful = (candidate is not None and candidate.route != position['remaining_route'] and
                      (not result.validation_result.valid or
                       (result.improvement is not None and result.improvement >= self.config.minimum_improvement)))
        key = tuple(candidate.route) if meaningful else None
        if key != self._pending_candidate:
            self._pending_candidate = key
            self._pending_since = self.now if key else None
        self._record_evidence('DECISION', planner_result=result,
                              remaining_route=position['remaining_route'], trigger_time=self._pending_since)
        if result.decision is PlannerOutcome.NO_ROUTE:
            self._handle_no_route(state, position)
        return result

    def handle_replan_result(self, result):
        if result is None or self.terminal_outcome:
            return result
        if result.decision is not PlannerOutcome.REPLAN:
            return result
        proposal = result.proposed_plan
        if proposal is None:
            self._record_evidence('REPLAN_EXECUTION_FAILED', reason='missing_proposal')
            return result
        if (self.active_plan is None or result.current_plan is None or
                result.current_plan.plan_id != self.active_plan.plan_id or
                proposal.ambulance_id != self.ambulance_id or
                proposal.hospital_id != self.hospital['id'] or
                proposal.revision != self.active_plan.revision + 1):
            self._record_evidence('REPLAN_VALIDATION_FAILED', reason='stale_or_mismatched_proposal')
            return result
        validation = validate_route(self.core.traci, proposal.ambulance_id, proposal.route, self.hospital)
        if not validation.valid:
            self._deferred = validation.deferred
            self._record_evidence('DEFERRED' if validation.deferred else 'REPLAN_VALIDATION_FAILED',
                                  validation=validation, requested_action=proposal.route)
            return result
        execution = self.core.execute_route(proposal.ambulance_id, proposal.route,
                                            proposal.plan_id, hospital=self.hospital)
        self._record_evidence('ROUTE_EXECUTION', validation=validation,
                              requested_action=proposal.route, execution=execution)
        if not execution.success:
            self._record_evidence('REPLAN_EXECUTION_FAILED', execution=execution,
                                  preserved_plan=self.active_plan)
            if not execution.safe_to_continue:
                self._finalize('EXECUTION_FAILED', 'physical_route_could_not_be_reconciled')
            return result
        # Only a verified physical action may advance the planner lifecycle.
        self.active_plan = self.replanner.accept(result, accepted_time=self.now)
        self.plan_history.append(deepcopy(self.active_plan))
        self.applied_replans += 1
        latency = self.now - (self._pending_since if self._pending_since is not None else self.now)
        self.replan_latencies.append(latency)
        self._record_evidence('REPLAN_ACCEPTED', accepted_plan=self.active_plan,
                              execution=execution, accepted_revision=self.active_plan.revision,
                              replanning_latency=latency)
        self._pending_candidate = self._pending_since = None
        self._record_advisories()
        return result

    def _handle_no_route(self, state, position):
        if self.routes == {}:
            self._finalize('NO_ROUTE', 'explicit_empty_candidates')
        elif not reachable_without_blocked(self.core.traci, self.ambulance_id,
                                          state['roads'], self.hospital, position):
            self._finalize('NO_ROUTE', 'hospital_unreachable_under_observed_blockages')
        else:
            self._record_evidence('NO_ROUTE_WAIT', reason='temporarily_unusable_or_candidate_limited',
                                  search_truncated=self._last_context.get('search_truncated', False))

    def _record_advisories(self):
        results = self.core.signal_executor.execute_advisory(self.active_plan)
        self._record_evidence('SIGNAL_ADVISORIES',
            recommendations=self.active_plan.recommendations.get('signal', []),
            advisory_results=results, execution_attempted=False)

    def _should_replan(self, events):
        triggers = {EventType.ROAD_BLOCKED, EventType.ROAD_UNBLOCKED,
                    EventType.CONGESTION_CHANGED, EventType.ROUTE_INVALIDATED}
        return any(e.event_type in triggers for e in events)

    def step(self, blocked_edges=None):
        if self.terminal_outcome:
            return self.core.city_state, [], None
        previous_vehicle = deepcopy(self.core.city_state.get_vehicle(self.ambulance_id))
        try:
            state, events, removals = self.core.step(blocked_edges=blocked_edges)
            outcome = self.core.city_state.terminal_vehicles.get(self.ambulance_id)
            if outcome is not None:
                self._record_evidence('LIFECYCLE_OBSERVATION', previous_vehicle=previous_vehicle,
                    removals=removals, events=events, latched_vehicle_outcome=outcome)
            if outcome == 'TELEPORTED':
                self._finalize('TELEPORTED', 'sumo_starting_teleport')
            elif outcome == 'ARRIVED':
                valid = (self.active_plan is not None and previous_vehicle is not None and
                         previous_vehicle.edge_id == self.active_plan.route[-1] and
                         previous_vehicle.route_index == len(previous_vehicle.route)-1 and
                         previous_vehicle.route[-1] == self.active_plan.route[-1] and
                         destination_matches(self.core.traci, previous_vehicle.edge_id, self.hospital))
                self._finalize('SUCCESS' if valid else 'FAILED_BLOCKED',
                               'verified_hospital_arrival' if valid else 'arrival_destination_unverified')
            elif outcome == 'DISAPPEARED':
                self._finalize('FAILED_BLOCKED', 'unexplained_disappearance')
            elif self.now >= self.config.horizon:
                self._finalize('TIMEOUT', 'simulation_horizon_reached')
            if self.terminal_outcome:
                return state, events, None
            periodic = self.now-self._last_evaluation >= self.config.reevaluation_interval
            if self.active_plan and (periodic or self._deferred or self._should_replan(events)):
                self._record_evidence('EVALUATION_TRIGGER', events=events, periodic=periodic)
                result = self.evaluate_replan()
                return state, events, self.handle_replan_result(result)
            if self.emergency and self.active_plan is None and (periodic or self._deferred):
                self.create_emergency_plan(self.emergency)
            return state, events, None
        except Exception as error:
            self._finalize('ERROR', f'{type(error).__name__}: {error}')
            return self.core.city_state, [], None

    def _finalize(self, outcome, reason):
        if self.terminal_outcome:
            return
        if outcome not in TERMINAL_OUTCOMES:
            raise ValueError('Unknown terminal outcome')
        self.terminal_outcome, self.terminal_reason = outcome, reason
        if outcome == 'SUCCESS':
            self.arrival_time = self.now
        self._record_evidence('TERMINAL', terminal_outcome=outcome, reason=reason,
                              last_accepted_plan=self.active_plan, metrics=self.summary())
        if self.ambulance_id:
            self.core.clear_active_route(self.ambulance_id)
            self.core.reserved_ambulances.discard(self.ambulance_id)
        self.active_plan = self.replanner.active_plan = None
        self.replanner.active_since = self.replanner.last_replan_time = None
        if self.writer:
            self.writer.summary(self.summary())

    def summary(self):
        return snapshot(dict(emergency_id=getattr(self.emergency, 'emergency_id', None),
            ambulance_id=self.ambulance_id, hospital=self.hospital,
            terminal_outcome=self.terminal_outcome, reason=self.terminal_reason,
            simulation_time=self.now, dispatch_time=self.dispatch_time, arrival_time=self.arrival_time,
            travel_time=self.arrival_time-self.dispatch_time if self.arrival_time is not None and self.dispatch_time is not None else None,
            route_changes=self.applied_replans, replanning_latencies=self.replan_latencies,
            accepted_plans=self.plan_history, configuration=self.config, provenance=self.provenance))

    def _record_evidence(self, action, **kwargs):
        evidence = snapshot(dict(action=action, simulation_time=self.now,
            emergency_id=getattr(self.emergency, 'emergency_id', None),
            ambulance_id=self.ambulance_id, hospital_id=(self.hospital or {}).get('id'),
            active_plan=self.active_plan, context=self._last_context, **kwargs))
        self.runtime_evidence.append(evidence)
        if self.writer:
            self.writer.append(evidence)


def run(config_path=None, max_steps=900, *, routes=None, hospitals=None, output=None, seed=1, config=None):
    path = Path(config_path or 'simulation/scenarios/S05_dynamic_blockage/S05.sumocfg').resolve()
    output = output or Path('data/output/integration') / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8])
    runtime = CityBrainRuntime(traci, routes, hospitals,
        config=config or RuntimeConfig(horizon=float(max_steps)), output=output)
    started = False
    try:
        root = Path(__file__).resolve().parents[1]
        source_hash = hashlib.sha256()
        for source in sorted((root/'citybrain').rglob('*.py')):
            source_hash.update(str(source.relative_to(root)).encode()); source_hash.update(source.read_bytes())
        inputs = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()}
        for tag in ('net-file', 'route-files', 'additional-files'):
            item = ET.parse(path).find(f'input/{tag}')
            if item is not None:
                for filename in item.get('value', '').split(','):
                    dependency = (path.parent/filename).resolve()
                    inputs[str(dependency)] = hashlib.sha256(dependency.read_bytes()).hexdigest()
        runtime.provenance = dict(
            git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
            working_tree_dirty=bool(subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip()),
            execution_sha256=source_hash.hexdigest(), inputs_sha256=inputs, seed=seed,
            python_version=platform.python_version(),
            sumo_version=subprocess.check_output([sumolib.checkBinary('sumo'), '--version'], text=True).splitlines()[0],
            started_at_utc=datetime.now(timezone.utc).isoformat())
        runtime._record_evidence('RUN_PROVENANCE', provenance=runtime.provenance)
        traci.start([sumolib.checkBinary('sumo'), '-c', str(path), '--seed', str(seed),
                     '--step-length', '1', '--end', str(max_steps), '--no-step-log', 'true'])
        started = True
        runtime.core.refresh_state()
        while not runtime.terminal_outcome:
            state, _, _ = runtime.step()
            if not runtime.emergency and not runtime.terminal_outcome:
                if any(v.vehicle_type == 'ambulance' for v in state.vehicles.values()):
                    runtime.create_emergency_plan(Emergency('EM-001', 'configured_emergency', 'HIGH', 'ROAD_ACCIDENT'))
    except Exception as error:
        runtime._finalize('ERROR', f'{type(error).__name__}: {error}')
    finally:
        if started:
            traci.close()
    print(json.dumps(runtime.summary(), indent=2))
    return runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', nargs='?')
    parser.add_argument('steps', nargs='?', type=int, default=900)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--routes', type=Path)
    parser.add_argument('--hospitals', type=Path)
    parser.add_argument('--topology-fallback', action='store_true')
    parser.add_argument('--reevaluation-interval', type=float, default=1.0)
    parser.add_argument('--minimum-improvement', type=float, default=5.0)
    parser.add_argument('--minimum-commitment', type=float, default=10.0)
    parser.add_argument('--cooldown', type=float, default=5.0)
    parser.add_argument('--candidate-limit', type=int, default=8)
    args = parser.parse_args()
    run(args.config, args.steps, output=args.output, seed=args.seed,
        config=RuntimeConfig(horizon=float(args.steps), topology_fallback=args.topology_fallback,
            reevaluation_interval=args.reevaluation_interval, minimum_improvement=args.minimum_improvement,
            minimum_commitment=args.minimum_commitment, cooldown=args.cooldown,
            candidate_limit=args.candidate_limit),
        routes=json.loads(args.routes.read_text()) if args.routes else None,
        hospitals=json.loads(args.hospitals.read_text()) if args.hospitals else None)


if __name__ == '__main__':
    main()
