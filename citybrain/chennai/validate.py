"""Read-only audits of Chennai execution and the frozen historical artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

from citybrain.chennai.network import ROOT, read_network


def historical_integrity():
    with tarfile.open(ROOT/'docs/final-integration-evidence.tar.gz') as archive:
        expected = json.load(archive.extractfile('verification/historical-hashes.json'))
    actual = {str(p.relative_to(ROOT)): p for p in (ROOT/'experiments/results').rglob('*') if p.is_file()}
    missing, extra = sorted(set(expected)-set(actual)), sorted(set(actual)-set(expected))
    hashes, sizes = [], []
    for name in set(expected) & set(actual):
        if hashlib.sha256(actual[name].read_bytes()).hexdigest() != expected[name]['sha256']:
            hashes.append(name)
        if actual[name].stat().st_size != expected[name]['size']:
            sizes.append(name)
    result = dict(expected=len(expected), actual=len(actual), missing=missing, extra=extra,
                  hash_mismatches=sorted(hashes), size_mismatches=sorted(sizes))
    if any([missing, extra, hashes, sizes]):
        raise ValueError(result)
    return result


def audit_run(directory):
    directory = Path(directory)
    summary = json.loads((directory/'runtime/summary.json').read_text())
    net = read_network()
    executions = {}
    revisions = []
    accepted = []
    terminal = []
    lifecycle = None
    actions = {}
    with (directory/'runtime/events.jsonl').open() as stream:
        for index, line in enumerate(stream):
            event = json.loads(line)
            action = event['action']
            actions[action] = actions.get(action, 0)+1
            if action in ('INITIAL_EXECUTION', 'ROUTE_EXECUTION') and event['execution']['success']:
                execution = event['execution']
                assert execution['verification'] == 'VERIFIED'
                assert execution['observed_suffix'] == execution['intended_suffix']
                assert execution['observed_route'][execution['route_index']:] == execution['intended_suffix']
                executions[execution['plan_id']] = index, execution
            if action in ('PLAN_ACCEPTED', 'REPLAN_ACCEPTED'):
                plan = event['accepted_plan']
                executed_index, execution = executions[plan['plan_id']]
                assert executed_index < index
                assert execution['intended_suffix'] == plan['route']
                assert plan['revision'] == len(revisions)
                assert plan['route'][-1] == summary['hospital']['destination_edge']
                for a,b in zip(plan['route'], plan['route'][1:]):
                    assert net.getEdge(b) in net.getEdge(a).getOutgoing()
                revisions.append(plan['revision'])
                accepted.append(dict(time=event['simulation_time'], revision=plan['revision'], route=plan['route']))
            if action == 'SIGNAL_ADVISORIES':
                assert event['execution_attempted'] is False
                assert all(r['executed'] is False for r in event['advisory_results'])
            if action == 'LIFECYCLE_OBSERVATION':
                lifecycle = event
            if action == 'TERMINAL':
                terminal.append(event['terminal_outcome'])
    assert terminal == [summary['terminal_outcome']]
    assert summary['route_changes'] == len(revisions)-1
    if summary['terminal_outcome'] == 'SUCCESS':
        assert lifecycle['latched_vehicle_outcome'] == 'ARRIVED'
        assert lifecycle['previous_vehicle']['edge_id'] == summary['hospital']['destination_edge']
        assert summary['arrival_time']-summary['dispatch_time'] == summary['travel_time']
    movement, phases, counts = {}, {}, []
    maximum_roundtrip_error = 0
    maximum_road_offset = 0
    with (directory/'telemetry.jsonl').open() as stream:
        for line in stream:
            frame = json.loads(line)
            counts.append(len(frame['vehicles']))
            for vehicle in frame['vehicles']:
                assert vehicle['source'] == 'SUMO_SIMULATED'
                assert vehicle['simulation_time'] == frame['simulation_time']
                lon, lat = vehicle['longitude'], vehicle['latitude']
                assert 79 < lon < 81 and 12 < lat < 14
                x,y = net.convertLonLat2XY(lon,lat)
                roundtrip = net.convertXY2LonLat(x,y)
                maximum_roundtrip_error=max(maximum_roundtrip_error,abs(roundtrip[0]-lon),abs(roundtrip[1]-lat))
                if vehicle['road'] and not vehicle['road'].startswith(':'):
                    from sumolib.geomhelper import distancePointToPolygon
                    maximum_road_offset=max(maximum_road_offset,
                        distancePointToPolygon((x,y),net.getEdge(vehicle['road']).getShape()))
                if vehicle['category'] == 'ambulance':
                    movement.setdefault(vehicle['id'], set()).add((lon,lat))
            for signal in frame['signals']:
                phases.setdefault(signal['signal_id'], set()).add(signal['state'])
    assert maximum_roundtrip_error < 1e-7
    assert maximum_road_offset < 15, maximum_road_offset
    assert movement and all(len(points)>10 for points in movement.values())
    assert phases and all(len(states)>1 for states in phases.values())
    return dict(terminal_outcome=summary['terminal_outcome'], arrival_time=summary['arrival_time'],
        dispatch_time=summary['dispatch_time'], travel_time=summary['travel_time'],
        route_changes=summary['route_changes'], accepted_plans=accepted, actions=actions,
        frames=len(counts), max_active_vehicles=max(counts),
        signal_states={k:sorted(v) for k,v in phases.items()},
        maximum_coordinate_roundtrip_error_degrees=maximum_roundtrip_error,
        maximum_vehicle_offset_from_edge_centerline_m=maximum_road_offset)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path)
    parser.add_argument('--historical', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = {}
    if args.historical:
        result['historical'] = historical_integrity()
    if args.run:
        result['chennai'] = audit_run(args.run)
    payload = json.dumps(result, indent=2)+'\n'
    if args.output:
        args.output.write_text(payload)
    print(payload)


if __name__ == '__main__':
    main()
