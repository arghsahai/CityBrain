"""Summarize every outcome; paired travel comparisons require two successful trips."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path
import statistics
import math


def mean_metric(rows, field):
    values = [float(row[field]) for row in rows if row.get(field) not in ('',None) and row['completion_status'] != 'ERROR']
    return f'{statistics.mean(values):.3f}' if values else 'NA'


def summarize(path):
    groups = defaultdict(list)
    with Path(path).open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        groups[(row['scenario'],row['profile'],row['strategy'])].append(row)
    lines = ['# SUMO experimental observations','',
             'Travel-time and ETA statistics exclude failures and teleports. No superiority claim is implied. ERROR rows retain their outcome but have no traffic measurements.','',
             '| Scenario | Profile | Strategy | Runs | Successes | Teleports | Mean travel s | Median travel s | SD s | Mean ETA error s |',
             '|---|---|---|---:|---:|---:|---:|---:|---:|---:|']
    summaries=[]
    for key, trials in sorted(groups.items()):
        successes=[r for r in trials if r['completion_status']=='SUCCESS' and r['completed']=='True' and r['teleported']=='False']
        times=[float(r['actual_travel_time']) for r in successes]
        n=len(trials);success=len(successes)
        teleports=sum(r['completion_status']=='TELEPORTED' for r in trials)
        applicable=key[0]!='S01'
        values=[f'{statistics.mean(times):.2f}',f'{statistics.median(times):.2f}',f'{statistics.stdev(times):.2f}' if len(times)>1 else 'NA',mean_metric(successes,'eta_error')] if times else ['NA']*4
        lines.append('| '+' | '.join([*key,str(n),str(success),str(teleports),*values])+' |')
        summaries.append(dict(scenario=key[0],profile=key[1],strategy=key[2],n=n,
            success_count=success,success_rate=success/n if applicable else '',
            failure_count=n-success if applicable else '',failure_rate=(n-success)/n if applicable else '',
            teleport_count=teleports,teleport_rate=teleports/n if applicable else '',
            travel_mean=statistics.mean(times) if times else '',travel_median=statistics.median(times) if times else '',
            travel_sd=statistics.stdev(times) if len(times)>1 else '',travel_min=min(times) if times else '',travel_max=max(times) if times else ''))
    lines += ['', '| Scenario | Profile | Strategy | Failure rate | Teleport rate | Travel min s | Travel max s |', '|---|---|---|---:|---:|---:|---:|']
    for row in summaries:
        lines.append('| '+' | '.join(str(row[k]) if row[k]!='' else 'NA' for k in ('scenario','profile','strategy','failure_rate','teleport_rate','travel_min','travel_max'))+' |')
    lines += ['', 'Normal traffic metrics include completed and unfinished background trips in a common 900-second window.','',
              '| Scenario | Profile | Strategy | Mean waiting s | Mean time loss s | Throughput veh/h | Route changes | Planner computation ms | Replan checks |',
              '|---|---|---|---:|---:|---:|---:|---:|---:|']
    for key,trials in sorted(groups.items()):
        fields=['normal_traffic_waiting_time','normal_traffic_time_loss','network_throughput_vehicles_per_hour','successful_route_changes','planner_computation_ms','replan_checks']
        lines.append('| '+' | '.join([*key,*[mean_metric(trials,f) for f in fields]])+' |')
    lines += ['', '95% Wilson intervals describe binomial success uncertainty; they are not superiority tests.','',
              '| Scenario | Profile | Strategy | Success rate | 95% Wilson interval |','|---|---|---|---:|---|']
    for row in summaries:
        if row['scenario']=='S01':continue
        n=row['n'];p=row['success_rate'];z=1.959963984540054;den=1+z*z/n
        center=(p+z*z/(2*n))/den;margin=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
        lines.append(f'| {row["scenario"]} | {row["profile"]} | {row["strategy"]} | {100*p:.1f}% | {100*(center-margin):.1f}%–{100*(center+margin):.1f}% |')
    paired=defaultdict(dict)
    for row in rows:
        key=(row['scenario'],row['profile'],row['seed'])
        if row['strategy'] in paired[key]:raise ValueError(f'Duplicate trial {key}')
        paired[key][row['strategy']]=row
    differences=defaultdict(list)
    for (scenario,profile,seed),pair in paired.items():
        if set(pair)=={'static','dynamic'} and all(r['completion_status']=='SUCCESS' for r in pair.values()):
            differences[(scenario,profile)].append(float(pair['static']['actual_travel_time'])-float(pair['dynamic']['actual_travel_time']))
    lines += ['', 'Paired travel differences (static minus dynamic, seconds) use only seeds where BOTH arrived. Read alongside all-run failure rates.','',
              '| Scenario | Profile | Successful pairs | Mean difference s | Median difference s | SD s | Min s | Max s |','|---|---|---:|---:|---:|---:|---:|---:|']
    for key,values in sorted(differences.items()):
        stats=[statistics.mean(values),statistics.median(values),statistics.stdev(values) if len(values)>1 else 0,min(values),max(values)]
        lines.append('| '+' | '.join([*key,str(len(values)),*[f'{v:.2f}' for v in stats]])+' |')
    lines += ['', 'All completion outcomes:','']
    for key,trials in sorted(groups.items()):
        counts={status:sum(r['completion_status']==status for r in trials) for status in sorted({r['completion_status'] for r in trials})}
        lines.append(f'- {" / ".join(key)}: {counts}')
    output=Path(path).with_suffix('.md');output.write_text('\n'.join(lines)+'\n')
    if summaries:
        with Path(path).with_name(Path(path).stem+'_statistics.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(summaries[0]),lineterminator='\n');writer.writeheader();writer.writerows(summaries)
    return output

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('csv',type=Path)
    summarize(parser.parse_args().csv)
