"""Read-only audit of a completed integration smoke directory."""
import argparse
import hashlib
import json
from pathlib import Path


def strict_json(text):
    def invalid(value): raise ValueError(f'Non-finite JSON token: {value}')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError(f'Duplicate key: {key}')
            result[key] = value
        return result
    return json.loads(text, parse_constant=invalid, object_pairs_hook=unique)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(directory):
    rows = strict_json((directory/'smokes.json').read_text())
    _require(bool(rows), 'No smoke results to verify')
    checks = []
    for row in rows:
        _require(row['finalized'], 'Active runtime state not finalized')
        path = directory/row['scenario']/'runtime'
        summary = strict_json((path/'summary.json').read_text())
        _require(all((row[key] == value for key, value in summary.items())), 'Summary disagreement')
        events = [strict_json(line) for line in (path/'events.jsonl').read_text().splitlines()]
        executions = {}; revisions = []; terminal = []
        for index, event in enumerate(events):
            if event['action'] in ('INITIAL_EXECUTION', 'ROUTE_EXECUTION'):
                execution = event['execution']
                if execution['success']:
                    _require(execution['verification'] == 'VERIFIED', 'Successful execution lacks VERIFIED status')
                    route = execution['intended_suffix']
                    _require(route and execution['physical_edge'] == route[0], 'Physical edge disagrees with intended suffix')
                    _require(execution['observed_suffix'] == route, 'Observed suffix differs from intended suffix')
                    _require(execution['observed_route'][execution['route_index']:] == route, 'Route index read-back disagrees with intended suffix')
                    executions[execution['plan_id']] = (index, execution)
            if event['action'] in ('PLAN_ACCEPTED', 'REPLAN_ACCEPTED'):
                plan = event['accepted_plan']
                executed_index, execution = executions[plan['plan_id']]
                _require(executed_index < index, 'Acceptance before execution')
                _require(plan['route'] == execution['intended_suffix'], 'Accepted route differs from executed route')
                _require(plan['revision'] == len(revisions), 'Revision skipped or repeated')
                _require(plan['hospital_id'] == summary['hospital']['id'], 'Accepted hospital differs from selected hospital')
                revisions.append(plan['revision'])
            if event['action'] == 'SIGNAL_ADVISORIES':
                _require(not event['execution_attempted'], 'Signal execution was attempted')
                _require(all((not r['executed'] and r['advisory'] for r in event['advisory_results'])), 'Signal result is not advisory-only')
            if event['action'] == 'TERMINAL':
                terminal.append(index)
        _require(len(terminal) == 1 and terminal[0] == len(events) - 1, 'Terminal state not final')
        _require(len(revisions) == len(summary['accepted_plans']), 'Accepted plan count disagrees with summary')
        _require(summary['route_changes'] == max(0, len(revisions) - 1), 'Route change count disagrees with revisions')
        _require(summary['terminal_outcome'] in {'SUCCESS', 'NO_ROUTE', 'FAILED_BLOCKED', 'TELEPORTED', 'TIMEOUT', 'EXECUTION_FAILED', 'ERROR'}, 'Unknown terminal outcome')
        if summary['terminal_outcome'] == 'SUCCESS':
            _require(summary['travel_time'] == summary['arrival_time'] - summary['dispatch_time'], 'Travel time disagrees with arrival and dispatch')
            observation = next(e for e in reversed(events) if e['action'] == 'LIFECYCLE_OBSERVATION')
            _require(observation['latched_vehicle_outcome'] == 'ARRIVED', 'Successful run lacks ARRIVED observation')
            _require(any((e['event_type'] == 'VEHICLE_ARRIVED' and e['entity_id'] == summary['ambulance_id'] for e in observation['events'])), 'Successful run lacks ambulance arrival event')
            _require(observation['previous_vehicle']['edge_id'] == summary['accepted_plans'][-1]['route'][-1], 'Arrival edge differs from accepted destination')
            _require(not any((e.get('latched_vehicle_outcome') == 'TELEPORTED' for e in events)), 'Successful run contains teleport evidence')
        else:
            _require(summary['travel_time'] is None and summary['arrival_time'] is None, 'Failed run has success-only timing metrics')
        for filename, digest in summary['provenance']['inputs_sha256'].items():
            _require(hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest, 'Input changed')
        checks.append(dict(scenario=row['scenario'], outcome=summary['terminal_outcome'],
                           accepted_revisions=revisions, evidence_records=len(events),
                           events_sha256=hashlib.sha256((path/'events.jsonl').read_bytes()).hexdigest()))
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory), indent=2))


if __name__ == '__main__': main()
