"""Run the local Chennai digital twin using the unchanged CityBrain runtime."""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
from pathlib import Path
import subprocess
import threading
import time
import webbrowser

import sumolib
import traci
from citybrain.main import RuntimeConfig
from citybrain.models.emergency import Emergency
from citybrain.chennai.network import ROOT, PILOT, NET, read_network
from citybrain.chennai.scenario import prepare, Disruptions
from citybrain.chennai.telemetry import DashboardWriter, emit
from citybrain.chennai.traffic import ReplayTrafficProvider, HERETrafficProvider, TomTomTrafficProvider
from citybrain.chennai.traffic.matching import RoadMatcher
from citybrain.chennai.traffic.service import TrafficService
from citybrain.chennai.gps import replay as gps_replay
from citybrain.chennai.stability import ChennaiRuntime, StabilityConfig


def run(output, profile='NORMAL', seconds_per_step=0.33, port=8770, serve=True,
        open_browser=True, mode='simulation', seed=17, horizon=1000, keep_open=False,
        confirmation_seconds=20.0, traffic_source=None, traffic_replay=None,
        authorize_traffic_requests=False, traffic_poll_seconds=60):
    output = Path(output).resolve()
    if output.is_relative_to(ROOT/'experiments/results'):
        raise ValueError('Pilot output cannot modify historical experiments')
    if not math.isfinite(seconds_per_step) or seconds_per_step < 0:
        raise ValueError('Pacing must be finite and nonnegative')
    stability_config = StabilityConfig(confirmation_seconds)
    traffic_source = traffic_source or {'live-assisted':'here','replay-assisted':'replay'}.get(mode,'simulation')
    provider = None
    if traffic_source == 'here':
        provider = HERETrafficProvider(authorized=authorize_traffic_requests)
    elif traffic_source == 'tomtom':
        provider = TomTomTrafficProvider(authorized=authorize_traffic_requests)
    elif traffic_source == 'replay':
        provider = ReplayTrafficProvider(traffic_replay or PILOT/'scenarios/traffic-sample-v22.json')
    elif traffic_source != 'simulation':
        raise ValueError('Unknown traffic source')
    observation_clock = [datetime(2026,10,16,tzinfo=timezone.utc) if traffic_source=='replay' else datetime.now(timezone.utc)]
    traffic_service = (TrafficService(provider,RoadMatcher(read_network()),poll_seconds=traffic_poll_seconds,
                                     clock=lambda:observation_clock[0]) if provider else None)
    output.mkdir(parents=True, exist_ok=False)
    cfg, metadata = prepare(output/'inputs', profile, seed)
    runtime = ChennaiRuntime(traci, routes=metadata['routes'], hospitals=[metadata['hospital']],
        stability_config=stability_config,
        config=RuntimeConfig(horizon=horizon, reevaluation_interval=10), output=output/'runtime')
    runtime.writer = DashboardWriter(runtime.writer, output/'dashboard.jsonl')
    runtime.provenance = dict(seed=seed, profile=profile, source='SUMO_SIMULATED',
        git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        working_tree_dirty=bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
        inputs_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [NET, cfg, cfg.parent/'traffic.rou.xml']},
        seconds_per_simulation_second=seconds_per_step, network=str(NET),
        soft_change_confirmation_seconds=confirmation_seconds,
        traffic_source=traffic_source, traffic_advisory_only=True,
        traffic_requests_authorized=authorize_traffic_requests,
        hospital_availability='SIMULATED; not verified clinical capacity')
    runtime._record_evidence('RUN_PROVENANCE', provenance=runtime.provenance)
    runtime._record_evidence('INCIDENT', location=[80.170, 12.829], source='SIMULATED_INCIDENT')
    server = None
    if serve:
        from citybrain.chennai.server import make_server
        server = make_server(output, port=port)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f'http://127.0.0.1:{server.server_port}'
        print('CITYBRAIN — CHENNAI DIGITAL TWIN: '+url, flush=True)
        if open_browser:
            webbrowser.open(url)
    gps_records = json.loads((PILOT/'scenarios/gps-replay.json').read_text()) if mode == 'replay-assisted' else []
    disruptions = Disruptions()
    started = False
    telemetry_failures = 0
    wall_start = time.monotonic()
    try:
        if traffic_service:
            traffic_service.start()
        traci.start([sumolib.checkBinary('sumo'), '-c', str(cfg), '--seed', str(seed),
            '--step-length', '1', '--end', str(horizon), '--no-step-log', 'true',
            '--duration-log.disable', 'true', '--xml-validation', 'never', '--error-log', str(output/'sumo-errors.log')])
        started = True
        runtime.core.refresh_state()
        while not runtime.terminal_outcome:
            step_start = time.monotonic()
            disruptions.update(runtime)
            state, _, _ = runtime.step()
            if not runtime.emergency and not runtime.terminal_outcome:
                if any(v.vehicle_type == 'ambulance' for v in state.vehicles.values()):
                    runtime.create_emergency_plan(Emergency('CHENNAI-001', metadata['origin_edge'], 'HIGH', 'ROAD_ACCIDENT'))
            # External/GPS observation errors cannot affect execution or cleanup.
            try:
                observation_clock[0] = (datetime(2026,10,16,tzinfo=timezone.utc)+timedelta(seconds=runtime.now)
                                        if traffic_source=='replay' else datetime.now(timezone.utc))
                if traffic_service:
                    traffic_service.notify_clock()
                external = traffic_service.snapshot() if traffic_service else dict(
                    source='UNAVAILABLE',provider='SIMULATION',status='SIMULATION_ONLY',observations=[],
                    match_status='NO VERIFIED ROAD MATCHES',applied_to_sumo=False)
            except Exception:
                external = dict(source='UNAVAILABLE', reason='External observation failed')
            try:
                gps = gps_replay(gps_records, datetime(2026,10,16,tzinfo=timezone.utc)+timedelta(seconds=runtime.now))
            except Exception:
                gps = []
            telemetry_failures += not emit(runtime, metadata['hospitals'], output/'telemetry.jsonl', external, gps)
            # Full evidence is already persisted; bound only the optional RAM cache.
            if len(runtime.runtime_evidence) > 64:
                del runtime.runtime_evidence[:-64]
            time.sleep(max(0, seconds_per_step-(time.monotonic()-step_start)))
    except KeyboardInterrupt:
        runtime._finalize('ERROR', 'operator_interrupted')
    except Exception as error:
        runtime._finalize('ERROR', f'{type(error).__name__}: {error}')
    finally:
        if traffic_service:
            traffic_service.stop()
        try:
            if started:
                traci.close()
        finally:
            if server:
                if keep_open and runtime.terminal_outcome:
                    print('Simulation complete. Dashboard remains available; Ctrl-C to close.', flush=True)
                    try:
                        while True:
                            time.sleep(0.5)
                    except KeyboardInterrupt:
                        pass
                server.shutdown()
                server.server_close()
            health = dict(telemetry_failures=telemetry_failures,
                dashboard_write_failures=runtime.writer.failures,
                traffic=traffic_service.snapshot() if traffic_service else None, wall_clock_seconds=time.monotonic()-wall_start,
                disruptions=disruptions.changes, summary=runtime.summary())
            (output/'health.json').write_text(json.dumps(health, indent=2)+'\n')
    return health


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['simulation', 'live-assisted', 'replay-assisted', 'replay'], default='simulation')
    parser.add_argument('--traffic-source', choices=['simulation','replay','here','tomtom'])
    parser.add_argument('--traffic-replay', type=Path, help='Normalized JSON recording with declared provenance')
    parser.add_argument('--traffic-poll-seconds', type=float, default=60)
    parser.add_argument('--authorize-traffic-requests', action='store_true',
                        help='Explicitly authorize potentially billable provider requests; keys alone do not authorize')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--events', type=Path, help='Completed Chennai output directory for replay')
    parser.add_argument('--profile', choices=['NORMAL', 'HEAVY', 'PEAK'], default='NORMAL')
    parser.add_argument('--seconds-per-step', type=float, default=0.33)
    parser.add_argument('--confirmation-seconds', type=float, default=20.0)
    parser.add_argument('--seed', type=int, default=17)
    parser.add_argument('--port', type=int, default=8770)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--no-server', action='store_true')
    parser.add_argument('--exit-on-complete', action='store_true')
    args = parser.parse_args()
    if args.mode == 'replay':
        if not args.events:
            parser.error('--events DIRECTORY is required for replay')
        from citybrain.chennai.server import make_server
        server = make_server(args.events, args.port, replay=True)
        url = f'http://127.0.0.1:{server.server_port}'
        print('CHENNAI REPLAY: '+url, flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return
    output = args.output or ROOT/'data/output/chennai'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    health = run(output, args.profile, args.seconds_per_step, args.port,
                 not args.no_server, not args.no_browser, args.mode,
                 seed=args.seed, keep_open=not args.exit_on_complete,
                 confirmation_seconds=args.confirmation_seconds, traffic_source=args.traffic_source,
                 traffic_replay=args.traffic_replay, traffic_poll_seconds=args.traffic_poll_seconds,
                 authorize_traffic_requests=args.authorize_traffic_requests)
    print(json.dumps(health, indent=2))
    if health['summary']['terminal_outcome'] != 'SUCCESS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
