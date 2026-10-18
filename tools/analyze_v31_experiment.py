"""Summarize the preregistered V3.1 matched SUMO run without exclusions."""
import csv
import gzip
import json
import random
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT/'data/output/v3-experiments/v31-matched-sumo-10seed-20261018'


def wilson(successes, n, z=1.959963984540054):
    if not n:
        return None
    p=successes/n
    denominator=1+z*z/n
    center=(p+z*z/(2*n))/denominator
    half=z*((p*(1-p)/n+z*z/(4*n*n))**0.5)/denominator
    return [max(0,center-half),min(1,center+half)]


def numeric(rows, key):
    return [float(r[key]) for r in rows if r.get(key) not in ('',None)]


def bootstrap_mean_interval(values, seed, replicates=10000):
    if not values:
        return None
    rng=random.Random(seed)
    means=sorted(sum(rng.choices(values,k=len(values)))/len(values) for _ in range(replicates))
    return [means[int(.025*replicates)],means[min(replicates-1,int(.975*replicates))]]


def main():
    rows=list(csv.DictReader((RUN/'results.csv').open()))
    expected={(s,seed,strategy) for s in ('S05','S06','S08') for seed in range(1,11)
              for strategy in ('static','dynamic')}
    observed={(r['scenario'],int(r['seed']),r['strategy']) for r in rows}
    if len(rows)!=60 or observed!=expected:
        raise SystemExit(f'Expected 60 unique planned trials; got {len(rows)} rows and {len(observed)} identities')
    for event_path in sorted(RUN.glob('*/events.json')):
        compressed=event_path.with_suffix('.json.gz')
        compressed.write_bytes(gzip.compress(event_path.read_bytes(),compresslevel=9,mtime=0))
    by={}
    for scenario in ('S05','S06','S08'):
        for strategy in ('static','dynamic'):
            subset=[r for r in rows if r['scenario']==scenario and r['strategy']==strategy]
            successes=[r for r in subset if r['completion_status']=='SUCCESS']
            teleports=[r for r in subset if r['completion_status']=='TELEPORTED']
            by[f'{scenario}/{strategy}']=dict(n=len(subset),successes=len(successes),
                success_rate=len(successes)/len(subset),success_wilson95=wilson(len(successes),len(subset)),
                teleports=len(teleports),teleport_rate=len(teleports)/len(subset),
                teleport_wilson95=wilson(len(teleports),len(subset)),
                outcomes={status:sum(r['completion_status']==status for r in subset)
                          for status in sorted({r['completion_status'] for r in subset})},
                successful_response_time_n=len(successes),
                successful_response_time_mean=(statistics.mean(numeric(successes,'response_time')) if successes else None),
                successful_response_time_median=(statistics.median(numeric(successes,'response_time')) if successes else None),
                successful_response_time_min=(min(numeric(successes,'response_time')) if successes else None),
                successful_response_time_max=(max(numeric(successes,'response_time')) if successes else None),
                mean_route_changes=statistics.mean(numeric(subset,'successful_route_changes')),
                mean_planner_computation_ms=statistics.mean(numeric(subset,'planner_computation_ms')),
                mean_replan_checks=statistics.mean(numeric(subset,'replan_checks')))
    paired={}
    for scenario in ('S05','S06','S08'):
        static={int(r['seed']):r for r in rows if r['scenario']==scenario and r['strategy']=='static'}
        dynamic={int(r['seed']):r for r in rows if r['scenario']==scenario and r['strategy']=='dynamic'}
        differences=[float(static[seed]['response_time'])-float(dynamic[seed]['response_time'])
            for seed in sorted(static.keys()&dynamic.keys())
            if static[seed]['completion_status']==dynamic[seed]['completion_status']=='SUCCESS']
        paired[scenario]=dict(successful_pairs=len(differences),
            response_difference_definition='static minus dynamic; seconds',
            response_mean_difference=(statistics.mean(differences) if differences else None),
            response_median_difference=(statistics.median(differences) if differences else None),
            response_difference_bootstrap95=bootstrap_mean_interval(differences,20261018+len(scenario)))
    manifest=json.loads((RUN/'manifest.json').read_text())
    report=dict(protocol_id='v31-matched-sumo-10seed-20261018',trials=len(rows),
        outcomes=by,paired=paired,provenance=dict(source='SUMO_SIMULATED',
        provider_observations_used=False,traffic_evaluator_arm_included=False,
        route_execution_readback='NOT MEASURED BY THIS LEGACY COMPARISON RUNNER',
        signals='SIMULATED; NO PRIORITY ACTUATION',gps='NO RUNTIME GPS INPUT',
        initial_trial_revision=manifest['git_commit'],
        aggregation_fix_revision=manifest.get('aggregation_amendment',{}).get('runner_fix_revision'),
        trial_resume_revision=manifest.get('aggregation_amendment',{}).get('resume_revision')),
        limitations=['10 matched seeds per scenario; one normal-demand profile and fixed synthetic inputs.',
        'Results do not test live traffic, the experimental traffic advisor, signal priority or GPS.',
        'Successful response-time summaries condition on SUCCESS; failures remain in completion denominators.',
        'N=10 intervals are broad; these scenario results do not establish general superiority or real-world performance.'])
    (RUN/'v31-analysis.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    lines=['# V3.1 matched SUMO experiment analysis','',
        'Protocol: [`V31_EXPERIMENT_PROTOCOL.md`](../../../../docs/V31_EXPERIMENT_PROTOCOL.md).',
        'Provenance: SUMO simulation only; no provider response, GPS runtime input, signal actuation or traffic-advisor selection.',
        'Matrix: 60 trials (3 scenarios × 10 seeds × 2 implemented arms); every recorded terminal outcome is included.',
        '', '| Scenario | Policy | n | SUCCESS | TELEPORTED | Other statuses | Success Wilson 95% | Successful response time mean (n) |',
        '|---|---|---:|---:|---:|---|---|---:|']
    for scenario in ('S05','S06','S08'):
        for strategy in ('static','dynamic'):
            d=by[f'{scenario}/{strategy}']; other={k:v for k,v in d['outcomes'].items() if k not in {'SUCCESS','TELEPORTED'}}
            interval=d['success_wilson95'];ci='NA' if interval is None else f'{interval[0]*100:.1f}%–{interval[1]*100:.1f}%'
            mean='NA' if d['successful_response_time_mean'] is None else f"{d['successful_response_time_mean']:.2f} ({d['successful_response_time_n']})"
            lines.append(f"| {scenario} | {strategy} | {d['n']} | {d['successes']} | {d['teleports']} | {other or 'none'} | {ci} | {mean} s |")
    lines += ['', '## Matched successful response-time differences', '',
        'Differences are static minus dynamic and include only seeds where both policies succeeded. Failed pairs remain represented above; they do not receive invented travel times.', '',
        '| Scenario | Successful pairs | Mean difference (s) | Median (s) | Bootstrap 95% interval (s) |',
        '|---|---:|---:|---:|---|']
    for scenario,d in paired.items():
        ci=d['response_difference_bootstrap95']
        lines.append(f"| {scenario} | {d['successful_pairs']} | {d['response_mean_difference'] if d['response_mean_difference'] is not None else 'Unavailable'} | {d['response_median_difference'] if d['response_median_difference'] is not None else 'Unavailable'} | {ci if ci is not None else 'Unavailable: no matched successes'} |")
    lines += ['', '## Interpretation and limits', '']+[f'- {item}' for item in report['limitations']]
    lines += ['', 'Replanning latency, route changes and planner computation are retained in `results.csv`; traffic freshness, geometry coverage and physical route read-back are not measured by this legacy static/dynamic harness. The dynamic arm has better observed completion in S05 and S08 in this sample, while S06 teleports in both arms. These outcomes are exploratory observations, not a general performance or operational claim.', '']
    (RUN/'v31-analysis.md').write_text('\n'.join(lines))
    print(json.dumps({'trials':len(rows),'outcomes':by,'paired':paired},indent=2))


if __name__=='__main__':
    main()
