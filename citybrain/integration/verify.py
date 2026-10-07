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


def verify(directory):
    rows = strict_json((directory/'smokes.json').read_text())
    checks = []
    for row in rows:
        assert row['finalized'], 'Active runtime state not finalized'
        path = directory/row['scenario']/'runtime'
        summary = strict_json((path/'summary.json').read_text())
        assert all(row[key] == value for key, value in summary.items()), 'Summary disagreement'
        events = [strict_json(line) for line in (path/'events.jsonl').read_text().splitlines()]
        executions = {}; revisions = []; terminal = []
        for index, event in enumerate(events):
            if event['action'] in ('INITIAL_EXECUTION', 'ROUTE_EXECUTION'):
                execution = event['execution']
                if execution['success']:
                    assert execution['verification'] == 'VERIFIED'
                    route = execution['intended_suffix']
                    assert route and execution['physical_edge'] == route[0]
                    assert execution['observed_suffix'] == route
                    assert execution['observed_route'][execution['route_index']:] == route
                    executions[execution['plan_id']] = (index, execution)
            if event['action'] in ('PLAN_ACCEPTED', 'REPLAN_ACCEPTED'):
                plan = event['accepted_plan']
                executed_index, execution = executions[plan['plan_id']]
                assert executed_index < index, 'Acceptance before execution'
                assert plan['route'] == execution['intended_suffix']
                assert plan['revision'] == len(revisions), 'Revision skipped or repeated'
                assert plan['hospital_id'] == summary['hospital']['id']
                revisions.append(plan['revision'])
            if event['action'] == 'SIGNAL_ADVISORIES':
                assert not event['execution_attempted']
                assert all(not r['executed'] and r['advisory'] for r in event['advisory_results'])
            if event['action'] == 'TERMINAL':
                terminal.append(index)
        assert len(terminal) == 1 and terminal[0] == len(events)-1, 'Terminal state not final'
        assert len(revisions) == len(summary['accepted_plans'])
        assert summary['route_changes'] == max(0, len(revisions)-1)
        assert summary['terminal_outcome'] in {'SUCCESS','NO_ROUTE','FAILED_BLOCKED','TELEPORTED','TIMEOUT','EXECUTION_FAILED','ERROR'}
        if summary['terminal_outcome'] == 'SUCCESS':
            assert summary['travel_time'] == summary['arrival_time']-summary['dispatch_time']
            observation = next(e for e in reversed(events) if e['action'] == 'LIFECYCLE_OBSERVATION')
            assert observation['latched_vehicle_outcome'] == 'ARRIVED'
            assert any(e['event_type'] == 'VEHICLE_ARRIVED' and e['entity_id'] == summary['ambulance_id']
                       for e in observation['events'])
            assert observation['previous_vehicle']['edge_id'] == summary['accepted_plans'][-1]['route'][-1]
            assert not any(e.get('latched_vehicle_outcome') == 'TELEPORTED' for e in events)
        else:
            assert summary['travel_time'] is None and summary['arrival_time'] is None
        for filename, digest in summary['provenance']['inputs_sha256'].items():
            assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest, 'Input changed'
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
