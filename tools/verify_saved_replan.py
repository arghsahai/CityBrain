"""Read-only audit of the preserved synthetic S08 multi-replan demonstration.

This verifies saved execution evidence, not a new trial or live Chennai run.
The archive does not contain original generated input files; their provenance
hashes are retained but cannot be independently recomputed from this archive.
"""
import hashlib
import json
from pathlib import Path
import tarfile
import xml.etree.ElementTree as ET

import sumolib

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT/'docs/krishna/s08-3d-demo-evidence.tar.gz'
EXPECTED_SHA256 = 'c7d53a707541f39baee33ee2258038c854adf34ceb14c72f680177a39980e834'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify():
    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    require(digest == EXPECTED_SHA256, 'Preserved demo archive checksum changed')
    with tarfile.open(ARCHIVE) as archive:
        require(set(archive.getnames()) == {'runtime/events.jsonl', 'runtime/summary.json',
                                           'demo.json', 'demo-health.json'}, 'Unexpected archive members')
        def read(name):
            member = archive.getmember(name)
            require(member.isfile() and member.size < 128*1024*1024, 'Invalid archive member')
            return archive.extractfile(member).read()
        event_bytes = read('runtime/events.jsonl')
        events = [json.loads(line) for line in event_bytes.splitlines()]
        summary = json.loads(read('runtime/summary.json'))
        metadata = json.loads(read('demo.json'))['demo_config']
        health = json.loads(read('demo-health.json'))
    net_path = ROOT/'simulation/network/research/city.net.xml'
    net = sumolib.net.readNet(str(net_path))
    shapes = {edge.get('id'): [lane.get('shape') for lane in edge.findall('lane')]
              for edge in ET.parse(net_path).findall('edge') if not edge.get('function')}
    require(shapes == metadata['road_edges'], 'Saved/current S08 road geometry differs')
    require(summary['provenance']['demo'] and 'synthetic' in metadata['label'], 'Missing synthetic demo provenance')
    executions, accepted, terminal = {}, [], []
    for index, event in enumerate(events):
        action = event['action']
        if action in {'INITIAL_EXECUTION', 'ROUTE_EXECUTION'} and event['execution']['success']:
            execution = event['execution']
            route = execution['intended_suffix']
            require(execution['verification'] == 'VERIFIED', 'Unverified execution')
            require(execution['observed_suffix'] == route == execution['observed_route'][execution['route_index']:], 'Read-back suffix mismatch')
            require(execution['physical_edge'] == route[0], 'Current physical edge mismatch')
            for edge_id in route:
                require(net.getEdge(edge_id).allows('emergency'), 'Emergency lane permission missing')
            for a, b in zip(route, route[1:]):
                require(any(c.allows('emergency') for c in net.getEdge(a).getOutgoing().get(net.getEdge(b), [])), 'Disconnected route')
            require(net.getEdge(route[-1]).getToNode().getID() == summary['hospital']['destination_junction'], 'Wrong hospital endpoint')
            executions[execution['plan_id']] = (index, execution)
        if action in {'PLAN_ACCEPTED', 'REPLAN_ACCEPTED'}:
            plan = event['accepted_plan']
            execution_index, execution = executions[plan['plan_id']]
            require(execution_index < index and execution['intended_suffix'] == plan['route'], 'Acceptance before matching execution')
            require(plan['revision'] == len(accepted), 'Revision sequence mismatch')
            if accepted:
                require(plan['parent_plan_id'] == accepted[-1]['plan_id'], 'Broken plan ancestry')
                require(execution['previous_suffix'] != plan['route'], 'Replan did not change physical suffix')
            accepted.append(dict(plan_id=plan['plan_id'], time=event['simulation_time'], revision=plan['revision'], route=plan['route']))
        if action == 'SIGNAL_ADVISORIES':
            require(not event['execution_attempted'] and all(not r['executed'] and r['advisory'] for r in event['advisory_results']), 'Signal actuation found')
        if action == 'TERMINAL':
            terminal.append(index)
    require(len(terminal) == 1 and all(e['action'] == 'DEMO_SNAPSHOT' for e in events[terminal[0]+1:]), 'Invalid terminal ordering')
    require(summary['terminal_outcome'] == 'SUCCESS' and summary['route_changes'] == len(accepted)-1 == 2, 'Expected saved two-replan success absent')
    require([a['time'] for a in accepted] == [301, 311, 316], 'Saved acceptance timestamps changed')
    lifecycle = next(e for e in reversed(events) if e['action'] == 'LIFECYCLE_OBSERVATION')
    require(lifecycle['latched_vehicle_outcome'] == 'ARRIVED', 'Missing latched arrival')
    require(not any(e.get('latched_vehicle_outcome') == 'TELEPORTED' for e in events), 'Teleport cannot be success')
    require(lifecycle['previous_vehicle']['edge_id'] == accepted[-1]['route'][-1], 'Arrival road mismatch')
    require(summary['travel_time'] == summary['arrival_time']-summary['dispatch_time'] == 124, 'Travel timing mismatch')
    require(health['telemetry_failures'] == 0, 'Saved telemetry failures')
    return dict(source='SAVED_SYNTHETIC_S08_GRID_DEMO', archive=str(ARCHIVE.relative_to(ROOT)),
                archive_sha256=digest, events_sha256=hashlib.sha256(event_bytes).hexdigest(),
                source_revision=summary['provenance']['git_commit'], records=len(events),
                accepted=accepted, route_changes=2, outcome='SUCCESS', arrival_time=summary['arrival_time'],
                travel_time=summary['travel_time'], geometry_matches_current_network=True,
                original_generated_input_hashes='PRESERVED, NOT RECOMPUTABLE FROM THIS ARCHIVE',
                chennai_guard='NOT A TEST OF THE CHENNAI 20-SECOND GUARD')


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
