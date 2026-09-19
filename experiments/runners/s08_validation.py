"""Run the fixed official S08 matrix only from a clean committed revision."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

import sumolib

from experiments.runners.compare import ROOT, initial_result, network_path, prepare_config, trial
from experiments.runners.s08_audit import validate_evidence
from experiments.runners.storage import fingerprint, validate_pairs, validate_row, write_csv, write_json

DEFINITION = ROOT/'experiments/configs/s08-validation.json'


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def committed_revision(root=ROOT):
    status = subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=root,text=True)
    if status.strip():
        raise ValueError('Official S08 runs require a clean committed working tree (including untracked files)')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()


def expected_keys(definition):
    return {(definition['scenario'],profile,seed,strategy)
            for profile in definition['profiles'] for seed in definition['seeds']
            for strategy in definition['strategies']}


def strict_json(path):
    def invalid(token):
        raise ValueError(f'Non-finite JSON token: {token}')
    def unique(pairs):
        result = {}
        for key,value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(Path(path).read_text(),parse_constant=invalid,object_pairs_hook=unique)


def environment_record(directory, profile, seed, definition):
    config = prepare_config(directory,'S08',profile)
    vehicles = ET.parse(directory/'routes.rou.xml').getroot()
    for identifier, when in definition['incident_departures_seconds'].items():
        if float(vehicles.find(f"vehicle[@id='{identifier}']").get('depart')) != when:
            raise ValueError('S08 blocker timing differs from the frozen definition')
    return dict(scenario='S08',profile=profile,seed=seed,
                network_sha256=sha256(network_path('S08')),
                routes_sha256=sha256(directory/'routes.rou.xml'),
                config_sha256=sha256(config),
                ambulance=vehicles.find("vehicle[@id='ambulance0']").attrib,
                hospital=definition['hospital'],horizon_seconds=definition['horizon_seconds'],
                step_seconds=definition['step_seconds'],
                incident_departures_seconds=definition['incident_departures_seconds'])


def validate_checkpoint(row, key):
    if set(row) != set(initial_result(*[key[0],key[3],key[2],key[1]])):
        raise ValueError('Malformed S08 checkpoint schema')
    if (row['scenario'],row['profile'],row['seed'],row['strategy']) != key:
        raise ValueError('Checkpoint identity mismatch')
    if type(row['completed']) is not bool or type(row['teleported']) is not bool or type(row['seed']) is not int:
        raise ValueError('Malformed checkpoint flag/seed types')
    for field in ('replan_checks','successful_route_changes','number_of_replans','candidate_evaluations'):
        if type(row[field]) is not int or row[field] < 0:
            raise ValueError('Malformed checkpoint counters')
    if row['number_of_replans'] != row['successful_route_changes']:
        raise ValueError('Inconsistent applied-replan counts')
    for field in ('scenario','profile','strategy','initial_route','final_route','completion_status','error'):
        if not isinstance(row[field],str):
            raise ValueError('Malformed checkpoint text fields')
    if type(row['route_changed']) is not bool or row['route_changed'] != (row['successful_route_changes'] > 0):
        raise ValueError('Inconsistent route-change flag')
    validate_row(row)
    if row['completed']:
        travel = row['ambulance_arrival_time'] - row['ambulance_dispatch_time']
        if not math.isclose(travel,row['actual_travel_time']) or not math.isclose(row['response_time'],row['ambulance_arrival_time']-row['accident_time']):
            raise ValueError('Inconsistent successful-trip timing')
    if row['strategy'] == 'static' and any(row[field] for field in ('replan_checks','successful_route_changes','candidate_evaluations')):
        raise ValueError('Static strategy contains dynamic planning')


def validate_complete(rows, definition):
    if len(rows) != definition['expected_trials'] or {(r['scenario'],r['profile'],r['seed'],r['strategy']) for r in rows} != expected_keys(definition):
        raise ValueError('Incomplete S08 matrix')
    validate_pairs(rows)


def run(output, resume=False):
    revision = committed_revision()
    definition = strict_json(DEFINITION)
    signature = dict(git_commit=revision,execution_fingerprint=fingerprint(ROOT),
                     definition_sha256=sha256(DEFINITION),matrix=definition,
                     python_version=platform.python_version(),
                     sumo_version=subprocess.check_output([sumolib.checkBinary('sumo'),'--version'],text=True).splitlines()[0],
                     network_sha256=sha256(network_path('S08')))
    manifest_path = output/'manifest.json'
    if output.exists():
        if not resume or not manifest_path.is_file():
            raise ValueError('Choose a new output directory or resume an existing matching official matrix')
        manifest = strict_json(manifest_path)
        if manifest['signature'] != signature:
            raise ValueError('Official resume revision/inputs/runtime do not match; do not mix implementations')
    else:
        output.mkdir(parents=True)
        manifest = dict(signature=signature,started_at_utc=utc_now(),completed_at_utc=None,completed_trials=0)
        write_json(manifest_path,manifest)
    rows = []
    for profile in definition['profiles']:
        for seed in definition['seeds']:
            pair_inputs = []
            for strategy in definition['strategies']:
                # Deliberately outside the trial ERROR handler: stop on implementation changes.
                if committed_revision() != revision or fingerprint(ROOT) != signature['execution_fingerprint'] or sha256(DEFINITION) != signature['definition_sha256']:
                    raise ValueError('Official execution changed: stop and create a new versioned matrix')
                key = ('S08',profile,seed,strategy)
                directory = output/f'S08_{profile}_{seed}_{strategy}'
                checkpoint = directory/'result.json'
                loaded_checkpoint = resume and checkpoint.exists()
                if loaded_checkpoint:
                    row = strict_json(checkpoint)
                    validate_checkpoint(row,key)
                    metadata = strict_json(directory/'provenance.json')
                    if metadata['git_commit'] != revision or metadata['result_sha256'] != sha256(checkpoint):
                        raise ValueError('Checkpoint provenance/result hash mismatch')
                    environment = metadata['environment']
                    for name, field in [('routes.rou.xml','routes_sha256'),('run.sumocfg','config_sha256')]:
                        if sha256(directory/name) != environment[field]:
                            raise ValueError('Checkpoint inputs changed')
                    events_path = directory/'events.json'
                    if events_path.exists():
                        if sha256(events_path) != metadata['events_sha256']:
                            raise ValueError('Checkpoint evidence changed')
                        validate_evidence(row,strict_json(events_path))
                    elif row['completion_status'] != 'ERROR':
                        raise ValueError('Missing decision evidence')
                    print('RESUME',*key,row['completion_status'],flush=True)
                else:
                    environment = environment_record(directory,profile,seed,definition)
                    started = utc_now()
                    try:
                        row = trial('S08',strategy,seed,profile,directory,horizon=definition['horizon_seconds'])
                    except Exception as error:
                        row = initial_result('S08',strategy,seed,profile)
                        row.update(completion_status='ERROR',error=f'{type(error).__name__}: {error}',
                                   normal_traffic_waiting_time='',normal_traffic_time_loss='',normal_traffic_arrivals='',
                                   network_throughput_vehicles_per_hour='',average_vehicle_speed='',planner_computation_ms='',runtime_seconds='')
                        write_json(checkpoint,row)
                    validate_checkpoint(row,key)
                    events_path = directory/'events.json'
                    write_json(directory/'provenance.json',dict(git_commit=revision,execution_fingerprint=signature['execution_fingerprint'],
                        started_at_utc=started,completed_at_utc=utc_now(),environment=environment,
                        result_sha256=sha256(checkpoint),events_sha256=sha256(events_path) if events_path.exists() else None))
                    print(*key,row['completion_status'],'changes',row['successful_route_changes'],flush=True)
                pair_inputs.append(environment)
                rows.append(row)
                if not loaded_checkpoint:
                    write_csv(output/'results.csv',rows)
            if pair_inputs[0] != pair_inputs[1]:
                raise ValueError('Static/dynamic environment mismatch')
    validate_complete(rows,definition)
    write_csv(output/'results.csv',rows)
    manifest.update(completed_at_utc=manifest['completed_at_utc'] or utc_now(),completed_trials=len(rows))
    write_json(manifest_path,manifest)
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    run(args.output,args.resume)

if __name__ == '__main__':
    main()
