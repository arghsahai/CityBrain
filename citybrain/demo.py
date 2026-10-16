"""Optional synthetic S08 presentation; no signal writes or second TraCI client."""
import argparse
import hashlib
import subprocess
import json
import math
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import sumolib
import traci
from citybrain.main import CityBrainRuntime, RuntimeConfig
from citybrain.models.emergency import Emergency
from citybrain.integration.state_adapter import CANDIDATE_ROUTES
from experiments.runners.compare import prepare_config, network_path


def observe(connection, runtime):
    """Read actual SUMO state using the already connected client."""
    vehicles = [dict(id=v, type=connection.vehicle.getTypeID(v),
        position=connection.vehicle.getPosition(v), edge=connection.vehicle.getRoadID(v),
        speed=connection.vehicle.getSpeed(v), angle=connection.vehicle.getAngle(v)) for v in connection.vehicle.getIDList()]
    signals = [dict(id=s, phase=connection.trafficlight.getPhase(s),
        state=connection.trafficlight.getRedYellowGreenState(s),
        next_switch=connection.trafficlight.getNextSwitch(s),
        position=connection.junction.getPosition(s)) for s in connection.trafficlight.getIDList()]
    return dict(vehicles=vehicles, signals=signals, hospitals=runtime.hospitals,
                hospital_position=connection.junction.getPosition('J9'))


def emit(connection, runtime, path):
    # Presentation failures cannot alter route acceptance, execution or cleanup.
    try:
        record = dict(action='DEMO_SNAPSHOT', simulation_time=runtime.now,
                      demo=observe(connection, runtime))
        with path.open('a') as stream:
            stream.write(json.dumps(record, allow_nan=False)+'\n')
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--seconds-per-step', type=float, default=1.8,
                        help='Wall seconds per simulated second after 280 s; 0 for verification')
    args = parser.parse_args()
    if not math.isfinite(args.seconds_per_step) or args.seconds_per_step < 0:
        parser.error('seconds-per-step must be finite and nonnegative')
    root = Path(__file__).resolve().parents[1]
    if args.output.resolve().is_relative_to(root/'experiments/results'):
        parser.error('Demo output must be outside official experiments/results')
    args.output.mkdir(parents=True, exist_ok=False)
    config = prepare_config(args.output/'inputs', 'S08', 'normal')
    # Only drawing attributes change; physical ambulance and car parameters stay frozen.
    routes = ET.parse(config.parent/'routes.rou.xml')
    ambulance = routes.find("vType[@id='ambulance']")
    ambulance.set('guiShape', 'emergency'); ambulance.set('color', '1,0.1,0.1')
    routes.write(config.parent/'routes.rou.xml')
    net = ET.parse(network_path('S08'))
    hospital = net.find("junction[@id='J9']")
    additional = ET.Element('additional')
    ET.SubElement(additional, 'poi', id='H1_SIMULATED_HOSPITAL', type='Simulated hospital',
        color='0,0.7,0.3', x=hospital.get('x'), y=hospital.get('y'), layer='100', width='18', height='18')
    ET.ElementTree(additional).write(config.parent/'demo.add.xml')
    tree = ET.parse(config)
    ET.SubElement(tree.find('input'), 'additional-files', value='demo.add.xml')
    tree.write(config)
    runtime = CityBrainRuntime(traci, CANDIDATE_ROUTES,
        config=RuntimeConfig(topology_fallback=True), output=args.output/'runtime')
    metadata = dict(action='DEMO_CONFIG', simulation_time=0, demo_config=dict(
        label='DEMO — synthetic SUMO S08', seconds_per_step=args.seconds_per_step,
        paced_from=280, hospital_availability='Synthetic configuration, not real hospital data',
        signals='Observed SUMO programs; CityBrain does not control signals'))
    metadata['demo_config']['roads'] = [lane.get('shape') for edge in net.findall('edge') if not edge.get('function') for lane in edge.findall('lane')]
    metadata['demo_config']['road_edges'] = {edge.get('id'): [lane.get('shape') for lane in edge.findall('lane')] for edge in net.findall('edge') if not edge.get('function')}
    metadata['demo_config']['bounds'] = [float(x) for x in net.find('location').get('convBoundary').split(',')]
    runtime.provenance = dict(git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(), demo=True, seed=1, inputs_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in config.parent.iterdir() if p.is_file()})
    runtime._record_evidence('RUN_PROVENANCE', provenance=runtime.provenance)
    runtime._record_evidence('DEMO_CONFIG', demo_config=metadata['demo_config'])
    (args.output/'demo.json').write_text(json.dumps(metadata, indent=2))
    started = False
    failures = 0
    try:
        command = [sumolib.checkBinary('sumo' if args.headless else 'sumo-gui'),
            '-c', str(config.resolve()), '--seed', '1', '--step-length', '1',
            '--end', '900', '--no-step-log', 'true']
        if not args.headless:
            command += ['--start', '--quit-on-end', '--delay', '0']
        traci.start(command); started = True
        runtime.core.refresh_state()
        while not runtime.terminal_outcome:
            wall_start = time.monotonic()
            state, _, _ = runtime.step()
            if not runtime.emergency and not runtime.terminal_outcome:
                if any(v.vehicle_type == 'ambulance' for v in state.vehicles.values()):
                    runtime.create_emergency_plan(Emergency('EM-001', 'configured_emergency', 'HIGH', 'ROAD_ACCIDENT'))
            failures += not emit(traci, runtime, args.output/'runtime/events.jsonl')
            if runtime.now >= 280:
                time.sleep(max(0, args.seconds_per_step-(time.monotonic()-wall_start)))
    except Exception as error:
        runtime._finalize('ERROR', f'{type(error).__name__}: {error}')
        raise
    finally:
        if started: traci.close()
        (args.output/'demo-health.json').write_text(json.dumps(dict(telemetry_failures=failures)))
    print(json.dumps(runtime.summary(), indent=2))
    if runtime.terminal_outcome != 'SUCCESS':
        raise SystemExit('Demo did not reach SUCCESS')


if __name__ == '__main__': main()
