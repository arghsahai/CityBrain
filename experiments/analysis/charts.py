"""Research charts with zero-based axes, failures retained and explicit missing values."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path
import statistics
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PROFILES=['normal','heavy','peak','congested']


def metric(rows, field, success_only=False):
    values=[float(row[field]) for row in rows if row.get(field) not in ('',None)
            and row['completion_status']!='ERROR' and (not success_only or row['completion_status']=='SUCCESS')]
    return statistics.mean(values) if values else math.nan


def charts(path):
    path=Path(path)
    with path.open(newline='') as file:rows=list(csv.DictReader(file))
    by_scenario=defaultdict(list)
    for row in rows:by_scenario[row['scenario']].append(row)
    outputs=[]
    for scenario,trials in sorted(by_scenario.items()):
        groups=defaultdict(list)
        for row in trials:groups[(row['profile'],row['strategy'])].append(row)
        keys=sorted(groups,key=lambda k:(PROFILES.index(k[0]),k[1]))
        labels=[f'{key[0]}\n{key[1]}\nn={len(groups[key])}' for key in keys]
        fig,axes=plt.subplots(3,2,figsize=(max(10,len(keys)*1.3),12),layout='constrained')
        metrics=[('Success rate (%)',lambda rs:100*sum(r['completion_status']=='SUCCESS' for r in rs)/len(rs) if scenario!='S01' else math.nan),
                 ('Successful emergency travel time (s)',lambda rs:metric(rs,'actual_travel_time',True)),
                 ('Normal traffic time loss (s)',lambda rs:metric(rs,'normal_traffic_time_loss')),
                 ('Successful route changes per trial',lambda rs:metric(rs,'successful_route_changes')),
                 ('Total planner computation per trial (ms)',lambda rs:metric(rs,'planner_computation_ms')),
                 ('First applied replan latency (simulation s)',lambda rs:metric(rs,'replanning_latency'))]
        for ax,(title,measure) in zip(axes.flat,metrics):
            values=[measure(groups[key]) for key in keys]
            ax.bar(labels,values,color=['#247ba0' if k[1]=='dynamic' else '#f29e4c' for k in keys])
            for index,value in enumerate(values):
                if math.isnan(value):ax.text(index,.03,'NA',transform=ax.get_xaxis_transform(),ha='center')
            ax.set_title(title,fontsize=11);ax.set_ylim(bottom=0);ax.grid(axis='y',alpha=.2)
        axes.flat[0].set_ylim(0,100)
        fig.suptitle(f'{scenario}: measured means across paired trials\nTravel time excludes failures; NA means no eligible observations',fontsize=12)
        output=path.with_name(path.stem+f'_{scenario}.png');fig.savefig(output,dpi=150);plt.close(fig);outputs.append(output)
    fig,axes=plt.subplots(1,max(1,len(by_scenario)),figsize=(max(6,6*len(by_scenario)),5),squeeze=False,layout='constrained')
    for ax,(scenario,trials) in zip(axes.flat,sorted(by_scenario.items())):
        available=[p for p in PROFILES if any(r['profile']==p for r in trials)]
        for strategy in ('static','dynamic'):
            values=[metric([r for r in trials if r['profile']==profile and r['strategy']==strategy],'actual_travel_time',True) for profile in available]
            ax.plot(available,values,marker='o',label=strategy)
        ax.set(title=scenario,ylabel='Mean successful travel time (s)',xlabel='Demand profile',ylim=(0,None));ax.legend();ax.grid(alpha=.2)
    fig.suptitle('Traffic demand and emergency travel time — successful trips only')
    output=path.with_name(path.stem+'_demand.png');fig.savefig(output,dpi=150);plt.close(fig);outputs.append(output)
    return outputs

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('csv',type=Path)
    charts(parser.parse_args().csv)
