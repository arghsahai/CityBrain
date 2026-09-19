"""Audit and summarize the frozen S08 matrix without altering any raw trial."""
import argparse
import csv
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics

from experiments.analysis.summarize import summarize
from experiments.runners.s08_validation import strict_json, sha256, validate_checkpoint, validate_complete
from experiments.runners.s08_audit import validate_evidence
from experiments.runners.storage import write_csv, write_json


def average(values):
    return statistics.mean(values) if values else ''


def audit(directory):
    manifest = strict_json(directory/'manifest.json')
    signature = manifest['signature'];definition = signature['matrix']
    rows=[];evidence=[];environments=defaultdict(dict)
    for profile in definition['profiles']:
        for seed in definition['seeds']:
            for strategy in definition['strategies']:
                key=('S08',profile,seed,strategy)
                trial=directory/f'S08_{profile}_{seed}_{strategy}'
                row=strict_json(trial/'result.json');validate_checkpoint(row,key)
                provenance=strict_json(trial/'provenance.json')
                if provenance['git_commit'] != signature['git_commit'] or provenance['execution_fingerprint'] != signature['execution_fingerprint']:
                    raise ValueError('Mixed official implementation provenance')
                if provenance['result_sha256'] != sha256(trial/'result.json'):
                    raise ValueError('Result hash mismatch')
                environment=provenance['environment']
                if (environment['scenario'],environment['profile'],environment['seed']) != key[:3]:
                    raise ValueError('Environment identity mismatch')
                if environment['network_sha256'] != signature['network_sha256']:
                    raise ValueError('Network hash mismatch')
                for name,field in [('routes.rou.xml','routes_sha256'),('run.sumocfg','config_sha256')]:
                    if environment[field] != sha256(trial/name):raise ValueError('Paired input hash mismatch')
                environments[(profile,seed)][strategy]=environment
                events_path=trial/'events.json'
                events=strict_json(events_path) if events_path.exists() else []
                if provenance['events_sha256'] != (sha256(events_path) if events_path.exists() else None):
                    raise ValueError('Evidence hash mismatch')
                validate_evidence(row,events)
                if row['completion_status'] != 'ERROR':
                    changes=[e for e in events if e['kind']=='MEANINGFUL_ENVIRONMENT_CHANGE']
                    applied=[e for e in events if e['kind']=='EVALUATION' and e['decision']=='APPLY']
                    for index,label in enumerate(('first','second')):
                        if row[f'{label}_environment_change_time'] != (changes[index]['time'] if len(changes)>index else ''):
                            raise ValueError('Change timestamp disagrees with evidence')
                        if row[f'{label}_applied_replan_time'] != (applied[index]['time'] if len(applied)>index else ''):
                            raise ValueError('Application timestamp disagrees with evidence')
                    for event in applied:
                        observed=event['observed_roads'];evaluations=event['candidate_evaluations']
                        valid_scores=[e['score'] for e in evaluations if e['valid']]
                        selected=[e for e in evaluations if e['route']==event['candidate_route']]
                        if not selected or not selected[0]['valid'] or selected[0]['score']!=min(valid_scores):
                            raise ValueError('Applied candidate does not match best recorded valid score')
                        evidence.append(dict(profile=profile,seed=seed,strategy=strategy,
                            time=event['time'],physical_edge=event['physical_edge'],distance_travelled_m=event['distance_travelled_m'],
                            reason=event['reason'],current_plan_score=event['current_plan_score'],candidate_score=selected[0]['score'],
                            predicted_benefit=event['predicted_benefit'],threshold_seconds=event['threshold_seconds'],
                            simulation_latency=event['simulation_latency'],route=event['application']['remaining_route_after']))
                rows.append(row)
    validate_complete(rows,definition)
    if manifest['completed_trials']!=definition['expected_trials'] or not manifest['completed_at_utc']:
        raise ValueError('Official manifest is not complete')
    for pair in environments.values():
        if pair['static']!=pair['dynamic']:raise ValueError('Unmatched strategy environments')
    return rows,manifest,evidence


def report(directory, output):
    if output.exists():raise ValueError('Choose a fresh analysis output directory')
    rows,manifest,evidence=audit(directory)
    output.mkdir(parents=True)
    write_csv(output/'results.csv',rows)
    summarize(output/'results.csv')
    write_json(output/'provenance.json',manifest)
    write_json(output/'applied_replans.json',evidence)
    groups=defaultdict(list)
    for row in rows:groups[(row['profile'],row['strategy'])].append(row)
    stats=[]
    for (profile,strategy),group in sorted(groups.items()):
        n=len(group);success=[r for r in group if r['completed']]
        teleports=sum(r['completion_status']=='TELEPORTED' for r in group)
        times=[r['actual_travel_time'] for r in success]
        changes=[r['successful_route_changes'] for r in group if r['completion_status']!='ERROR']
        latencies=[e['simulation_latency'] for e in evidence if e['profile']==profile and e['strategy']==strategy]
        stats.append(dict(profile=profile,strategy=strategy,n=n,success_count=len(success),success_rate=len(success)/n,
            teleport_count=teleports,teleport_rate=teleports/n,other_failure_count=n-len(success)-teleports,
            other_failure_rate=(n-len(success)-teleports)/n,
            travel_mean=average(times),travel_median=statistics.median(times) if times else '',
            travel_sd=statistics.stdev(times) if len(times)>1 else '',
            zero_replans=changes.count(0),one_replan=changes.count(1),two_plus_replans=sum(c>=2 for c in changes),
            unknown_replans=n-len(changes),zero_replans_percent=100*changes.count(0)/n,
            one_replan_percent=100*changes.count(1)/n,two_plus_replans_percent=100*sum(c>=2 for c in changes)/n,
            mean_route_changes=average(changes),mean_applied_replan_latency=average(latencies)))
    with (output/'s08_statistics.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(stats[0]),lineterminator='\n');writer.writeheader();writer.writerows(stats)
    repeated=[r for r in rows if r['strategy']=='dynamic' and r['completion_status']!='ERROR' and r['successful_route_changes']>=2]
    category='REPEATED MULTI-REPLAN EVIDENCE' if len({r['seed'] for r in repeated})>=2 and len({r['profile'] for r in repeated})>=2 else 'IMPLEMENTATION DEMONSTRATION ONLY'
    lines=['# S08 continuous-replanning validation','',f'Generating commit: `{manifest["signature"]["git_commit"]}`.',
        '',f'**Evidence classification: {category}.**',
        '', 'This classification follows the predeclared rule. One fixed synthetic network and incident schedule cannot establish robustness to timing/topology changes or real emergency traffic.',
        '', '| Profile | Strategy | n | Success | Teleport | Other failure | Mean successful travel s | Median s | SD s | 0 replans | 1 replan | 2+ replans |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for s in stats:
        fields=['profile','strategy','n','success_count','teleport_count','other_failure_count','travel_mean','travel_median','travel_sd','zero_replans','one_replan','two_plus_replans']
        lines.append('| '+' | '.join('NA' if s[f]=='' else f'{s[f]:.2f}' if isinstance(s[f],float) else str(s[f]) for f in fields)+' |')
    lines+=['','Dynamic distribution (denominator: all 10 dynamic trials per profile):','']
    for s in stats:
        if s['strategy']=='dynamic':lines.append(f'- {s["profile"]}: 0 = {s["zero_replans"]} ({s["zero_replans_percent"]:.0f}%); 1 = {s["one_replan"]} ({s["one_replan_percent"]:.0f}%); 2+ = {s["two_plus_replans"]} ({s["two_plus_replans_percent"]:.0f}%); unknown = {s["unknown_replans"]}.')
    lines+=['',f'{len(evidence)} physically applied replans passed evidence checks; {len(repeated)} dynamic trials had at least two applied replans.',
        '', 'Successful-trip means condition on survival and must be read beside failure rates. See results.md for matched-success paired differences and full outcome counts. Static trials make zero Replanner calls and apply zero post-dispatch CityBrain route changes.',
        '', 'The observed-change timestamps label E7/E11 deterioration relative to dispatch; they are not incident insertion times, and are separate from the first gate-eligible candidate and its application. A positive physical distance establishes post-dispatch motion; the instantaneous speed may be zero at a signal.',
        '', 'The prior S05/S07 120-trial baseline is unchanged. S06 remains the unreachable-destination case. The optional 560-trial suite was not executed. Hardware remains future work.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')
    plot(stats,output)
    return stats,category


def plot(stats,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import math
    profiles=['normal','heavy','peak']
    fig,axes=plt.subplots(2,2,figsize=(12,9),layout='constrained')
    for strategy,color,offset in [('static','#f29e4c',-.18),('dynamic','#247ba0',.18)]:
        selected=[next(s for s in stats if s['profile']==p and s['strategy']==strategy) for p in profiles]
        positions=[i+offset for i in range(3)]
        axes[0,0].bar(positions,[100*s['success_rate'] for s in selected],width=.34,color=color,label=strategy)
        axes[0,1].bar(positions,[s['travel_mean'] if s['travel_mean']!='' else math.nan for s in selected],width=.34,color=color,label=strategy)
        for i,s in enumerate(selected):
            axes[0,0].text(positions[i],min(96,100*s['success_rate']+3),f'T={s["teleport_count"]}; F={s["other_failure_count"]}',ha='center',fontsize=8)
            if s['travel_mean']=='':axes[0,1].text(positions[i],.03,'NA',transform=axes[0,1].get_xaxis_transform(),ha='center')
        axes[1,1].bar(positions,[s['mean_applied_replan_latency'] if s['mean_applied_replan_latency']!='' else math.nan for s in selected],width=.34,color=color,label=strategy)
    bottoms=[0]*3
    for field,label,color in [('zero_replans','0','#adadad'),('one_replan','1','#f29e4c'),('two_plus_replans','2+','#247ba0'),('unknown_replans','Unknown','#c44e52')]:
        values=[next(s for s in stats if s['profile']==p and s['strategy']=='dynamic')[field] for p in profiles]
        axes[1,0].bar(range(3),values,bottom=bottoms,label=label,color=color)
        bottoms=[a+b for a,b in zip(bottoms,values)]
    titles=['Success rate (%) — T: teleports; F: other failures','Mean successful-trip travel time (s) — NA: no successes','Dynamic route-change distribution (10 trials/profile)','Mean per-applied-replan latency (simulation s)']
    for ax,title in zip(axes.flat,titles):
        ax.set_title(title,fontsize=10);ax.set_xticks(range(3),profiles);ax.set_ylim(bottom=0);ax.legend();ax.grid(axis='y',alpha=.2)
    axes[0,0].set_ylim(0,110);axes[1,0].set_ylim(0,10)
    fig.suptitle('S08: 60 paired synthetic trials; fixed configuration, seeds 1–10')
    fig.savefig(output/'s08_validation.png',dpi=160);plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report(args.directory,args.output)

if __name__ == '__main__':main()
