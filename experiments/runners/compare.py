"""Paired, headless SUMO trials using the existing CityBrain planner interfaces."""
import argparse
import contextlib
import copy
import csv
import hashlib
import subprocess
import io
import json
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import sumolib
import traci

from citybrain.integration.state_adapter import build_state
from citybrain.models.emergency import Emergency
from citybrain.planner.emergency_planner import EmergencyPlanner
from citybrain.planner.replanner import Replanner
from experiments.outcomes import classify_step
from experiments.runners.s08_audit import S08Audit, ScoreRecorder, decision_reason, encode_evidence, validate_evidence
from experiments.runners.storage import fingerprint, write_json, write_csv, validate_row, validate_pairs

ROOT = Path(__file__).resolve().parents[2]
PROFILES = {"normal": 1, "heavy": 1.5, "peak": 2, "congested": 3}


def network_path(scenario):
    return ROOT / ('simulation/network/research/city.net.xml' if scenario == 'S08' else 'simulation/network/regression/city.net.xml')


def prepare_config(directory, scenario, profile):
    directory.mkdir(parents=True, exist_ok=True)
    tree = ET.parse(ROOT / 'simulation/scenarios/S05_dynamic_blockage/dynamic_blockage.rou.xml')
    routes = tree.getroot()
    for flow in routes.findall('flow'):
        multiplier = max(PROFILES[profile], 1.5) if scenario == "S03" else PROFILES[profile]
        flow.set('vehsPerHour', str(float(flow.get('vehsPerHour')) * multiplier))
    # Keep stochastic car-following and ordinary intersection rules; no blue-light bypass.
    routes.find("vType[@id='ambulance']").set('vClass', 'emergency')
    if scenario == 'S01':
        for vehicle in list(routes.findall('vehicle')):
            routes.remove(vehicle)
    elif scenario in ('S02', 'S03', 'S07'):
        routes.remove(routes.find("vehicle[@id='dynamic_blocker']"))
    elif scenario == 'S04':
        routes.find("vehicle[@id='dynamic_blocker']").set('depart', '295')
    elif scenario in ('S06', 'S08'):
        ET.SubElement(routes, 'route', id='secondBlockageRoute', edges='E11')
        vehicle = ET.SubElement(routes, 'vehicle', id='second_blocker', type='accidentVehicle',
                                route='secondBlockageRoute', depart='315' if scenario == 'S08' else '310', departPos='20', departSpeed='0')
        ET.SubElement(vehicle, 'stop', lane='E11_0', endPos='30', duration='600')
    if scenario == 'S07':
        ET.SubElement(routes, 'vType', id='slowCar', vClass='passenger', maxSpeed='3', accel='2.6', decel='4.5', sigma='0.5')
        ET.SubElement(routes, 'route', id='queueRoute', edges='E7 E23')
        ET.SubElement(routes, 'flow', id='queue', type='slowCar', route='queueRoute', begin='305', end='450', vehsPerHour='1800')
    # SUMO requires demand records in chronological order.
    demand = list(routes.findall('flow')) + list(routes.findall('vehicle'))
    for element in demand:
        routes.remove(element)
    for element in sorted(demand, key=lambda item: float(item.get('begin', item.get('depart', '0')))):
        routes.append(element)
    tree.write(directory / 'routes.rou.xml', encoding='utf-8', xml_declaration=True)
    config = ET.Element('configuration')
    inputs = ET.SubElement(config, 'input')
    ET.SubElement(inputs, 'net-file', value=str(network_path(scenario)))
    ET.SubElement(inputs, 'route-files', value='routes.rou.xml')
    ET.ElementTree(config).write(directory / 'run.sumocfg')
    return directory / 'run.sumocfg'


def remaining_routes(state, ambulance):
    """Limit candidates to reachable suffixes, without changing teammate routing code."""
    edge = traci.vehicle.getRoadID(ambulance)
    if edge.startswith(':'):
        return False
    state['routes'] = {key: route[route.index(edge):] for key, route in state['routes'].items() if edge in route}
    return bool(state['routes'])


def initial_result(scenario, strategy, seed, profile):
    result = dict(scenario=scenario, strategy=strategy, seed=seed, profile=profile,
                  accident_time=300, blockage_time=307 if scenario in ('S05', 'S06', 'S08') else '',
                  initial_route='', final_route='', initial_eta='', replanned_eta='',
                  blockage_detection_time='', replanning_trigger_time='', replanning_completion_time='',
                  ambulance_dispatch_time='', ambulance_arrival_time='', actual_travel_time='',
                  response_time='', eta_error='', number_of_replans=0, successful_route_changes=0,
                  route_changed=False, replanning_latency='', planner_computation_ms=0,
                  replan_checks=0, runtime_seconds=0, error='', completion_status='TIMEOUT', teleported=False, completed=False,
                  normal_traffic_waiting_time=0, normal_traffic_time_loss=0, normal_traffic_arrivals=0,
                  network_throughput_vehicles_per_hour=0, average_vehicle_speed=0)
    if scenario == 'S08':
        result.update(candidate_evaluations=0, first_environment_change_time='',
                      second_environment_change_time='', first_applied_replan_time='',
                      second_applied_replan_time='', first_applied_replan_latency='',
                      second_applied_replan_latency='')
    return result


def trial(scenario, strategy, seed, profile, directory, horizon=900, gui=False, demo=False):
    config = prepare_config(directory, scenario, profile)
    result = initial_result(scenario, strategy, seed, profile)
    wall_start = time.perf_counter()
    planner, replanner = EmergencyPlanner(), Replanner()
    audit = S08Audit() if scenario == 'S08' else None
    if audit:
        planner.route_scorer = ScoreRecorder(planner.route_scorer)
        replanner.route_scorer = ScoreRecorder(replanner.route_scorer)
    emergency = Emergency('EM001', 'J3', 'HIGH', 'ROAD_ACCIDENT')
    plan = None
    blocked = set()
    first_blockage_detection = None
    last_evaluation = -10
    last_change = -10
    pending_candidate = None
    pending_since = None
    events = []
    traffic_samples = []
    edge_samples = []
    traci.start([sumolib.checkBinary('sumo-gui' if gui else 'sumo'), '-c', str(config),
                 '--seed', str(seed), '--step-length', '1', '--end', str(horizon),
                 '--tripinfo-output', str(directory / 'tripinfo.xml'),
                 '--tripinfo-output.write-unfinished', 'true', '--no-step-log', 'true',
                 '--duration-log.disable', 'true'] + (['--start','--quit-on-end','--delay','100'] if gui else []))
    try:
        while traci.simulation.getTime() < horizon and traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            now = traci.simulation.getTime()
            ids = traci.vehicle.getIDList()
            new_blocked = set()
            for blocker in ('accident_blocker', 'dynamic_blocker', 'second_blocker'):
                if blocker in ids and traci.vehicle.isStopped(blocker):
                    new_blocked.add(traci.vehicle.getRoadID(blocker))
            changed = new_blocked != blocked
            if changed:
                events.append(dict(time=now, kind='STATE_CHANGE', blocked_edges=sorted(new_blocked), previous_blocked_edges=sorted(blocked)))
                if demo: print(f'[{now:.0f}s] State change: blocked={sorted(new_blocked)}', flush=True)
            blocked = new_blocked
            if 'E7' in blocked and first_blockage_detection is None:
                first_blockage_detection = now
                result['blockage_detection_time'] = now
            if now % 10 == 0:
                for edge in ('E3','E5','E7','E19','E11'):
                    edge_samples.append(dict(time=now, edge=edge, vehicle_count=traci.edge.getLastStepVehicleNumber(edge),
                                             mean_speed=traci.edge.getLastStepMeanSpeed(edge),
                                             occupancy_percent=traci.edge.getLastStepOccupancy(edge),
                                             queue_length_vehicles=traci.edge.getLastStepHaltingNumber(edge),
                                             travel_time=traci.edge.getTraveltime(edge)))
            cars = [v for v in ids if traci.vehicle.getTypeID(v) in ('car', 'slowCar')]
            if cars:
                traffic_samples.append(sum(traci.vehicle.getSpeed(v) for v in cars) / len(cars))
            if plan is not None and not result['completed'] and result['completion_status'] == 'TIMEOUT':
                outcome = classify_step(plan.ambulance_id, ids, traci.simulation.getArrivedIDList(),
                                        traci.simulation.getStartingTeleportIDList())
                if outcome:
                    events.append(dict(time=now, kind='OUTCOME', status=outcome))
                    if demo: print(f'[{now:.0f}s] Ambulance outcome: {outcome}', flush=True)
                    result['completion_status'] = outcome
                    result['teleported'] = outcome == 'TELEPORTED'
                    result['completed'] = outcome == 'SUCCESS'
                    if result['completed']:
                        result['ambulance_arrival_time'] = now
                        result['actual_travel_time'] = now - result['ambulance_dispatch_time']
                        result['response_time'] = now - 300
                        result['eta_error'] = abs(result['actual_travel_time'] - result['initial_eta'])
            if scenario == 'S01' or now < 300 or (plan is not None and result['completion_status'] != 'TIMEOUT'):
                continue
            state = build_state(blocked_edges=blocked)
            if scenario == 'S08':
                state['routes'] = {**state['routes'], 'R_EM_5': ['E13','E5','E19','E27','E33','E30']}
            if audit and plan is not None:
                changes = audit.observe_changes(now, state['roads'])
                events.extend(changes)
                for change in changes:
                    field = 'first_environment_change_time' if change['change_ordinal'] == 1 else 'second_environment_change_time'
                    result[field] = now
            if plan is None:
                if not state['ambulances']:
                    continue
                if not remaining_routes(state, state['ambulances'][0]['id']):
                    continue
                start = time.perf_counter()
                with contextlib.redirect_stdout(io.StringIO()):
                    candidate = planner.create_plan(emergency, state)
                result['planner_computation_ms'] += (time.perf_counter() - start) * 1000
                if candidate is None:
                    result['completion_status'] = 'NO_ROUTE'
                    continue
                traci.vehicle.setRoute(candidate.ambulance_id, candidate.route)
                plan = candidate
                result.update(initial_route=' -> '.join(plan.route), final_route=' -> '.join(plan.route),
                              initial_eta=plan.eta, ambulance_dispatch_time=now, completion_status='TIMEOUT')
                events.append(dict(time=now, kind='DISPATCH', ambulance=plan.ambulance_id, hospital=plan.hospital_id, route=list(plan.route), eta=plan.eta, decision='APPLY'))
                if demo: print(f'[{now:.0f}s] P0 dispatched: {plan.ambulance_id} -> {plan.hospital_id}; route={plan.route}; ETA={plan.eta:.2f}s', flush=True)
                if audit:
                    audit.observe_changes(now, state['roads'])
                    events[-1].update(physical_edge=traci.vehicle.getRoadID(plan.ambulance_id),
                        observed_roads=copy.deepcopy(state['roads']),
                        candidate_routes=copy.deepcopy(state['routes']),
                        candidate_evaluations=copy.deepcopy(planner.route_scorer.records),
                        application=dict(time=now, route_after=list(traci.vehicle.getRoute(plan.ambulance_id))))
                last_change = now
            elif strategy == 'dynamic' and (changed or now - last_evaluation >= 1):
                last_evaluation = now
                if not remaining_routes(state, plan.ambulance_id):
                    continue
                current = list(traci.vehicle.getRoute(plan.ambulance_id))[traci.vehicle.getRouteIndex(plan.ambulance_id):]
                invalid = any(edge in blocked for edge in current)
                if audit:
                    replanner.route_scorer.records.clear()
                result['replan_checks'] += 1
                start = time.perf_counter()
                with contextlib.redirect_stdout(io.StringIO()):
                    candidate = replanner.replan(copy.deepcopy(plan), state)
                elapsed = (time.perf_counter() - start) * 1000
                result['planner_computation_ms'] += elapsed
                old_eta = sum(state['roads'][e]['travel_time'] for e in current)
                benefit = old_eta - candidate.eta if candidate else None
                meaningful = bool(candidate and candidate.route != current and
                                  (invalid or benefit >= max(5, old_eta * .15)))
                route_key = tuple(candidate.route) if meaningful else None
                if route_key != pending_candidate:
                    pending_candidate = route_key
                    pending_since = now if meaningful else None
                apply = meaningful and (invalid or now-last_change >= 10)
                event = dict(time=now, kind='EVALUATION', minimum_commitment_seconds=10, minimum_benefit_seconds=5, minimum_benefit_fraction=.15, seconds_since_assignment=now-last_change, threshold_seconds=max(5,old_eta*.15), reason=('no_reachable_candidate' if candidate is None else 'blocked_route' if invalid else 'benefit_and_commitment_gate'), trigger='blocked_remaining_route' if invalid else 'periodic_traffic_evaluation',
                             blocked_edges=sorted(blocked), old_route=current,
                             candidate_route=candidate.route if candidate else [], old_eta=old_eta,
                             candidate_eta=candidate.eta if candidate else None, predicted_benefit=benefit,
                             planner_computation_ms=elapsed, decision='APPLY' if apply else 'KEEP')
                if audit:
                    recorded = copy.deepcopy(replanner.route_scorer.records)
                    audit.candidate_evaluations += len(recorded)
                    event.update(physical_edge=traci.vehicle.getRoadID(plan.ambulance_id),
                        physical_speed_m_s=traci.vehicle.getSpeed(plan.ambulance_id),
                        distance_travelled_m=traci.vehicle.getDistance(plan.ambulance_id),
                        sumo_route_before=list(traci.vehicle.getRoute(plan.ambulance_id)),
                        observed_roads=copy.deepcopy(state['roads']),
                        candidate_routes=copy.deepcopy(state['routes']), candidate_evaluations=recorded,
                        current_plan_score=replanner.route_scorer.scorer.calculate_score(current,state),
                        current_route_invalid=invalid, gate_passed=bool(apply),
                        reason=decision_reason(candidate,current,invalid,benefit,max(5,old_eta*.15),now-last_change))
                if apply:
                    try:
                        traci.vehicle.setRoute(candidate.ambulance_id, candidate.route)
                    except traci.TraCIException as error:
                        event.update(decision='APPLY_FAILED', error=str(error))
                    else:
                        plan = candidate
                        if demo: print(f'[{now:.0f}s] P{result["successful_route_changes"]+1} physically applied: {plan.route}; reason={event["reason"]}', flush=True)
                        last_change = now
                        result['number_of_replans'] += 1
                        result['successful_route_changes'] += 1
                        result.update(final_route=' -> '.join(plan.route), replanned_eta=plan.eta, route_changed=True)
                        event.update(trigger_time=pending_since, completion_time=now,
                                     simulation_latency=now-pending_since)
                        if result['replanning_latency'] == '':
                            result['replanning_latency'] = now-pending_since
                            result['replanning_trigger_time'] = pending_since
                            result['replanning_completion_time'] = now
                        if audit:
                            event['application'] = dict(time=now,
                                route_after=list(traci.vehicle.getRoute(plan.ambulance_id)),
                                route_index_after=traci.vehicle.getRouteIndex(plan.ambulance_id),
                                remaining_route_after=list(traci.vehicle.getRoute(plan.ambulance_id))[traci.vehicle.getRouteIndex(plan.ambulance_id):],
                                command='traci.vehicle.setRoute', returned_without_exception=True)
                            ordinal = result['successful_route_changes']
                            if ordinal in (1,2):
                                label = 'first' if ordinal == 1 else 'second'
                                result[f'{label}_applied_replan_time'] = now
                                result[f'{label}_applied_replan_latency'] = now-pending_since
                        pending_candidate = None
                        pending_since = None
                events.append(event)
    finally:
        if audit:
            write_json(directory/'events.json', encode_evidence(events))
        traci.close()
    trips = ET.parse(directory / 'tripinfo.xml').getroot().findall('tripinfo')
    cars = [t for t in trips if t.get('vType') in ('car', 'slowCar')]
    arrived = [t for t in cars if float(t.get('arrival')) >= 0]
    result.update(normal_traffic_waiting_time=sum(float(t.get('waitingTime')) for t in cars)/max(1,len(cars)),
                  normal_traffic_time_loss=sum(float(t.get('timeLoss')) for t in cars)/max(1,len(cars)),
                  normal_traffic_arrivals=len(arrived), network_throughput_vehicles_per_hour=len(arrived)*3600/horizon,
                  average_vehicle_speed=sum(traffic_samples)/max(1,len(traffic_samples)))
    if scenario == 'S01':
        result['completion_status'] = 'NOT_APPLICABLE'
    elif plan is None:
        result['completion_status'] = 'NO_ROUTE'
    with (directory/'edges.csv').open('w', newline='') as file:
        if edge_samples:
            writer = csv.DictWriter(file, fieldnames=list(edge_samples[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(edge_samples)
    result['runtime_seconds'] = time.perf_counter() - wall_start
    if audit:
        result['candidate_evaluations'] = audit.candidate_evaluations
        events = encode_evidence(events)
        validate_evidence(result, events)
    validate_row(result)
    write_json(directory/'events.json', events)
    write_json(directory/'result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenarios', nargs='+', choices=['S01','S02','S03','S04','S05','S06','S07','S08'], default=['S05'])
    parser.add_argument('--seeds', nargs='+', type=int, default=list(range(1,11)))
    parser.add_argument('--profiles', nargs='+', choices=list(PROFILES), default=['normal'])
    parser.add_argument('--output', type=Path, default=ROOT/'experiments/results/paired')
    parser.add_argument('--gui', action='store_true')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if len(set(args.seeds)) != len(args.seeds) or any(seed < 0 for seed in args.seeds):
        parser.error('Seeds must be unique nonnegative integers')
    if len(set(args.scenarios)) != len(args.scenarios) or len(set(args.profiles)) != len(args.profiles):
        parser.error('Scenarios and profiles must be unique')
    signature = dict(scenarios=args.scenarios, profiles=args.profiles, seeds=args.seeds,
                     input_sha256=fingerprint(ROOT), horizon_seconds=900,
                     sumo_version=subprocess.check_output([sumolib.checkBinary('sumo'),'--version'],text=True).splitlines()[0])
    manifest_path = args.output/'manifest.json'
    if args.output.exists():
        if not args.resume or not manifest_path.is_file():
            parser.error('Use a fresh output directory or --resume with an existing matching manifest')
        if json.loads(manifest_path.read_text())['signature'] != signature:
            parser.error('Resume inputs/code differ from manifest; use a fresh output directory')
    else:
        args.output.mkdir(parents=True)
        write_json(manifest_path, dict(signature=signature,
                   git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                   evaluation_interval_seconds=1, commitment_seconds=10, benefit_seconds=5, benefit_fraction=.15))
    rows = []
    for scenario in args.scenarios:
        for profile in args.profiles:
            for seed in args.seeds:
                for strategy in ('static','dynamic'):
                    directory = args.output/f'{scenario}_{profile}_{seed}_{strategy}'
                    checkpoint = directory/'result.json'
                    if args.resume and checkpoint.exists():
                        row = json.loads(checkpoint.read_text())
                        validate_row(row)
                        if (row['scenario'],row['profile'],row['seed'],row['strategy']) != (scenario,profile,seed,strategy):
                            raise ValueError(f'Checkpoint identity mismatch: {checkpoint}')
                        print('RESUME', scenario, profile, seed, strategy, flush=True)
                    else:
                        try:
                            row = trial(scenario,strategy,seed,profile,directory,gui=args.gui)
                        except Exception as error:
                            # Keep infrastructure failures explicit. KeyboardInterrupt remains interruptible.
                            row = initial_result(scenario,strategy,seed,profile)
                            row.update(completion_status='ERROR', error=f'{type(error).__name__}: {error}',
                                       normal_traffic_waiting_time='', normal_traffic_time_loss='',
                                       normal_traffic_arrivals='', network_throughput_vehicles_per_hour='',
                                       average_vehicle_speed='', planner_computation_ms='', runtime_seconds='')
                            directory.mkdir(parents=True,exist_ok=True)
                            write_json(checkpoint,row)
                        print(scenario,profile,seed,strategy,row['completion_status'],row['actual_travel_time'],flush=True)
                    rows.append(row)
                    write_csv(args.output/'results.csv',rows)
    validate_pairs(rows)
    from experiments.analysis.summarize import summarize
    summarize(args.output/'results.csv')

if __name__ == '__main__':
    main()
