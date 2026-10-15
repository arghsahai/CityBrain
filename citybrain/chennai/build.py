"""Reproducible local OSM import. No fabricated geometry and no paid services."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.request import urlopen, Request

import sumolib
from citybrain.chennai.network import PILOT, NET, BOUNDS, prepare_metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true', help='Fetch a fresh OSM extract explicitly')
    args = parser.parse_args()
    source = PILOT/'network/chennai.osm.xml'
    url = 'https://www.openstreetmap.org/api/0.6/map?bbox=80.125,12.815,80.185,12.865'
    if args.download or not source.exists():
        with urlopen(Request(url, headers={'User-Agent': 'CityBrain-University-Pilot/2.0'}), timeout=60) as response:
            payload = response.read(30_000_001)
        if len(payload) > 30_000_000 or b'<osm' not in payload[:1000]:
            raise ValueError('Not a bounded OSM XML extract')
        source.write_bytes(payload)
    binary = sumolib.checkBinary('netconvert')
    env = dict(os.environ)
    # Some macOS framework installations point SUMO_HOME above share/sumo.
    for base in [Path(env.get('SUMO_HOME', '/nonexistent')), Path(binary).resolve().parents[1]/'share/sumo']:
        if (base/'data/typemap/osmNetconvert.typ.xml').exists():
            env['SUMO_HOME'] = str(base)
            break
    with tempfile.TemporaryDirectory(prefix='citybrain-osm-') as tmp:
        raw = Path(tmp)/'raw.net.xml'
        commands = [[binary, '--osm-files', str(source), '--type-files', str(PILOT/'network/osmNetconvert.typ.xml'),
            '--output-file', str(raw), '--geometry.remove', '--roundabouts.guess', '--ramps.guess',
            '--junctions.join', '--keep-edges.by-vclass', 'passenger,emergency', '--no-turnarounds',
            '--output.street-names', 'true', '--xml-validation', 'never']]
        subprocess.run(commands[0], check=True, env=env, capture_output=True)
        net = sumolib.net.readNet(str(raw))
        keep = []
        for edge in net.getEdges():
            lon, lat = net.convertXY2LonLat(*edge.getShape()[len(edge.getShape())//2])
            if edge.allows('passenger') and BOUNDS[0] <= lon <= BOUNDS[2] and BOUNDS[1] <= lat <= BOUNDS[3]:
                keep.append(edge.getID())
        selection = Path(tmp)/'edges.txt'
        selection.write_text('\n'.join(keep))
        commands.append([binary, '--sumo-net-file', str(raw), '--keep-edges.input-file', str(selection),
            '--output-file', str(NET), '--tls.set', 'cluster_1945600982_308878067,7732945699',
            '--no-turnarounds', '--xml-validation', 'never'])
        result = subprocess.run(commands[-1], check=True, env=env, capture_output=True, text=True)
        (PILOT/'network/import-warnings.txt').write_text(result.stderr)
    data = prepare_metadata()
    # Keep the connected arterial study corridors and all validated diversions;
    # avoid thousands of cul-de-sac residential edges dominating each Core scan.
    net = sumolib.net.readNet(str(NET))
    corridor = {e.getID() for e in net.getEdges() if e.getType() != 'highway.residential'}
    corridor.update(e for path in data['routes'].values() for e in path)
    from citybrain.chennai.network import shortest
    for hospital in data['hospitals']:
        corridor.update(shortest(net, data['origin_edge'], hospital['destination_edge']) or [])
    for edge_id in list(corridor):
        corridor.update(e.getID() for e in net.getEdge(edge_id).getOutgoing())
    with tempfile.TemporaryDirectory(prefix='citybrain-corridor-') as tmp:
        selected = Path(tmp)/'corridor.txt'
        selected.write_text('\n'.join(sorted(corridor)))
        output = Path(tmp)/'corridor.net.xml'
        command = [binary, '--sumo-net-file', str(NET), '--keep-edges.input-file', str(selected),
                   '--output-file', str(output), '--xml-validation', 'never']
        result = subprocess.run(command, check=True, env=env, capture_output=True, text=True)
        shutil.copyfile(output, NET)
        with (PILOT/'network/import-warnings.txt').open('a') as stream:
            stream.write(result.stderr)
        commands.append(command)
    data = prepare_metadata()
    provenance = dict(source_url=url, imported_at_utc=datetime.now(timezone.utc).isoformat(), license='ODbL-1.0',
        attribution='© OpenStreetMap contributors', source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        network_sha256=hashlib.sha256(NET.read_bytes()).hexdigest(),
        netconvert_version=subprocess.check_output([binary, '--version'], text=True).splitlines()[0],
        commands=[[str(x).replace(str(PILOT.parents[1]), '<REPO>') for x in c] for c in commands],
        selection='Main-road corridor in 4.6 × 4.4 km envelope: primary/tertiary roads, legal alternate emergency paths, hospital access paths and one-hop feeders; full selected edge geometry retained.',
        vit_verification='OSM way 336095563 contains the VIT campus; reference 12.8408,80.1540 lies within its mapped boundary.',
        limitations=['OSM completeness and restrictions are not a ground survey.',
                      'Two simulated signals added at real junctions; not evidence of physical traffic lights.',
                      'Nearest reachable hospital road is not a verified driveway or emergency entrance.'])
    provenance['restriction_audit'] = ('Source no_right_turn relation 17954113 references ways outside the retained corridor. '
        'Retained routes follow imported SUMO lane connections; no surveyed local restriction dataset is available.')
    (PILOT/'network/provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    print(json.dumps({k: data[k] for k in ['edge_count', 'signal_count', 'route_lengths_m']}, indent=2))


if __name__ == '__main__':
    main()
