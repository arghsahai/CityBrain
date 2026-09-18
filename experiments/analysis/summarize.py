"""Summarize all outcomes; travel-time statistics include successful arrivals only."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path
import statistics


def summarize(path):
    groups = defaultdict(list)
    with Path(path).open(newline='') as stream:
        for row in csv.DictReader(stream):
            groups[(row['scenario'], row['profile'], row['strategy'])].append(row)
    lines = ['# SUMO experimental observations', '',
             'Travel-time and ETA statistics exclude failures and teleports. No superiority claim is implied.', '',
             '| Scenario | Profile | Strategy | Runs | Successes | Teleports | Mean travel s | Median travel s | SD s | Mean ETA error s |',
             '|---|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for key, rows in sorted(groups.items()):
        successes = [r for r in rows if r['completion_status'] == 'SUCCESS' and r['completed'] == 'True' and r['teleported'] == 'False']
        times = [float(r['actual_travel_time']) for r in successes]
        errors = [float(r['eta_error']) for r in successes]
        values = [f'{statistics.mean(times):.2f}', f'{statistics.median(times):.2f}', f'{statistics.stdev(times):.2f}' if len(times)>1 else 'NA', f'{statistics.mean(errors):.2f}'] if times else ['NA']*4
        lines.append('| '+' | '.join([*key,str(len(rows)),str(len(successes)),str(sum(r['completion_status']=='TELEPORTED' for r in rows)),*values])+' |')
    lines += ['', 'Normal traffic metrics include completed and unfinished background vehicles over the same 900-second window.', '',
              '| Scenario | Profile | Strategy | Mean waiting s | Mean time loss s | Mean throughput veh/h | Mean route changes | Mean planner computation ms |',
              '|---|---|---|---:|---:|---:|---:|---:|']
    for key, rows in sorted(groups.items()):
        metrics = ['normal_traffic_waiting_time','normal_traffic_time_loss','network_throughput_vehicles_per_hour','successful_route_changes','planner_computation_ms']
        if all(metric in rows[0] for metric in metrics):
            values = [f'{statistics.mean(float(row[metric]) for row in rows):.3f}' for metric in metrics]
            lines.append('| '+' | '.join([*key,*values])+' |')
    output = Path(path).with_suffix('.md')
    output.write_text('\n'.join(lines)+'\n')
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    summarize(parser.parse_args().csv)
