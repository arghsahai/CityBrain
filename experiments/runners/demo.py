"""One-command professor demo using the same validated experiment loop."""
import argparse
from datetime import datetime
from pathlib import Path
from experiments.runners.compare import ROOT, trial

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gui',action='store_true')
    parser.add_argument('--scenario',choices=['S05','S07','S08'],default='S05')
    parser.add_argument('--seed',type=int,default=1)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    directory=args.output or ROOT/'experiments/results'/('demo-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    if directory.exists():parser.error('Choose a fresh output directory')
    print('CityBrain started: software + SUMO; incident at 300 s; hospital H1 at J9.',flush=True)
    result=trial(args.scenario,'dynamic',args.seed,'normal',directory,gui=args.gui,demo=True)
    print(f'Finished: {result["completion_status"]}; travel={result["actual_travel_time"]} s; route changes={result["successful_route_changes"]}')
    print(f'Metrics and decision log: {directory}')

if __name__ == '__main__':main()
