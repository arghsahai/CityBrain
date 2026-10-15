"""Read-only acceptance and future-route oscillation audit of existing evidence.

Repeated suffix returns are a stability-review flag, not proof that each proposal
had an equal score. This tool does not change simulation or planner behavior.
"""
import argparse
import hashlib
import json
from pathlib import Path


def audit(events, minimum_commitment=10):
    executions = {}
    accepted = []
    last_decision = None
    returns = []
    overrides = []
    for index, event in enumerate(events):
        action = event['action']
        if action in ('INITIAL_EXECUTION', 'ROUTE_EXECUTION'):
            execution = event['execution']
            if execution['success']:
                assert execution['verification'] == 'VERIFIED'
                assert execution['intended_suffix'] == execution['observed_suffix']
                executions[execution['plan_id']] = index, execution
        if action == 'DECISION':
            last_decision = event
        if action not in ('PLAN_ACCEPTED', 'REPLAN_ACCEPTED'):
            continue
        plan = event['accepted_plan']
        execution_index, execution = executions[plan['plan_id']]
        assert execution_index < index
        assert execution['intended_suffix'] == plan['route']
        assert plan['revision'] == len(accepted)
        row = dict(time=event['simulation_time'], revision=plan['revision'],
                   plan_id=plan['plan_id'], route=plan['route'], execution_verified=True)
        if action == 'REPLAN_ACCEPTED':
            assert last_decision is not None
            result = last_decision['planner_result']
            assert result['proposed_plan']['plan_id'] == plan['plan_id']
            previous = last_decision['remaining_route']
            assert previous != plan['route'], 'Accepted replan does not change physical suffix'
            common = []
            for old, new in zip(previous, plan['route']):
                if old != new:
                    break
                common.append(old)
            earlier = [p['revision'] for p in accepted[:-1]
                       if plan['route'][0] in p['route'] and
                       p['route'][p['route'].index(plan['route'][0]):] == plan['route']]
            row.update(reason=result['reason'], current_score=result['current_score'],
                proposed_score=result['proposed_score'], improvement=result['improvement'],
                threshold=result['threshold'], elapsed_since_acceptance=row['time']-accepted[-1]['time'],
                common_prefix_edges=len(common), divergence_after_edge=common[-1] if common else None,
                returned_to_revisions=earlier)
            if earlier and common:
                returns.append(dict(time=row['time'], revision=row['revision'], earlier_revisions=earlier))
            if result['reason'].startswith('invalid_active_route_override:'):
                invalidated = result['validation_result'].get('invalidated_component')
                road = last_decision.get('context', {}).get('planner_state', {}).get('roads', {}).get(invalidated, {})
                override = dict(time=row['time'], revision=row['revision'], edge=invalidated,
                    road_observation=road, elapsed_since_acceptance=row['elapsed_since_acceptance'],
                    below_minimum_commitment=row['elapsed_since_acceptance'] < minimum_commitment)
                overrides.append(override)
        accepted.append(row)
    assert accepted, 'No accepted plans found'
    return dict(accepted_plans=accepted, physically_verified_route_changes=len(accepted)-1,
        repeated_future_suffix_returns=returns, invalid_route_overrides=overrides,
        stability_status='OSCILLATION_REVIEW_REQUIRED' if returns else 'NO_REPEATED_FUTURE_SUFFIX_RETURN_OBSERVED',
        limitation='A suffix return proves repeated selection, not equal scores or a counterfactual travel-time loss.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('events', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    digest = hashlib.sha256()
    def records():
        with args.events.open('rb') as stream:
            for line in stream:
                digest.update(line)
                yield json.loads(line)
    result = audit(records())
    result.update(source_file=str(args.events), source_sha256=digest.hexdigest())
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'accepted_plans'}, indent=2))


if __name__ == '__main__':
    main()
