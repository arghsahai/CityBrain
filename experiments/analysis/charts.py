"""Export comparisons with zero-based axes and all trial outcomes visible."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path
import statistics
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def charts(path):
    groups = defaultdict(list)
    with Path(path).open(newline='') as file:
        for row in csv.DictReader(file):
            groups[(row['scenario'], row['profile'], row['strategy'])].append(row)
    keys = sorted(groups)
    labels = ['\n'.join(key) for key in keys]
    fig, axes = plt.subplots(2, 2, figsize=(max(8,len(keys)*1.4),8), layout='constrained')
    metrics = [('Success rate (%)', lambda rows: 100*sum(r['completion_status']=='SUCCESS' for r in rows)/len(rows) if any(r['completion_status']!='NOT_APPLICABLE' for r in rows) else math.nan),
               ('Successful emergency travel time (s)', lambda rows: statistics.mean([float(r['actual_travel_time']) for r in rows if r['completion_status']=='SUCCESS']) if any(r['completion_status']=='SUCCESS' for r in rows) else math.nan),
               ('Mean normal traffic time loss (s)', lambda rows: statistics.mean(float(r['normal_traffic_time_loss']) for r in rows)),
               ('Route changes per trial', lambda rows: statistics.mean(float(r['successful_route_changes']) for r in rows))]
    for ax, (title, measure) in zip(axes.flat, metrics):
        values = [measure(groups[key]) for key in keys]
        ax.bar(labels, values)
        for index, value in enumerate(values):
            if math.isnan(value):
                ax.text(index, .03, 'NA', transform=ax.get_xaxis_transform(), ha='center')
        ax.set_title(title)
        ax.set_ylim(bottom=0)
        ax.grid(axis='y', alpha=.2)
    axes.flat[0].set_ylim(0,100)
    fig.suptitle('SUMO observations: means across all trials\nTravel time excludes failures; NA indicates no applicable or successful trips', fontsize=11)
    output = Path(path).with_suffix('.png')
    fig.savefig(output, dpi=160)
    plt.close(fig)
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    charts(parser.parse_args().csv)
