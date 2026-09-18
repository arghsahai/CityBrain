"""Rebuild the committed network from its node, edge and signal sources."""
import argparse
from pathlib import Path
import subprocess
import sumolib
from experiments.runners.compare import ROOT

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    network = ROOT/'simulation/network'
    subprocess.run([sumolib.checkBinary('netconvert'), '--node-files', str(network/'city.nod.xml'),
                    '--edge-files', str(network/'city.edg.xml'),
                    '--output-file', str(args.output)], check=True)

if __name__ == '__main__':
    main()
