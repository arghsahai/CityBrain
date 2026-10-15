"""Synthetic demand and explicit, reproducible simulation-only disruptions."""
import json
from pathlib import Path
import random
import xml.etree.ElementTree as ET
from citybrain.chennai.network import NET, PILOT, read_network, shortest

PROFILES = {'NORMAL': 0.7, 'HEAVY': 1.4, 'PEAK': 2.2}


def prepare(directory, profile='NORMAL', seed=17):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    net = read_network()
    metadata = json.loads((PILOT/'network/metadata.json').read_text())
    rng = random.Random(seed)
    edges = [e.getID() for e in net.getEdges() if e.allows('passenger') and e.getLength() > 30]
    major = [e.getID() for e in net.getEdges() if e.getType() in ('highway.primary', 'highway.tertiary')]
    paths = []
    for _ in range(500):
        start, end = rng.choice(major), rng.choice(edges)
        path = shortest(net, start, end)
        if path and len(path) >= 6 and sum(net.getEdge(e).getLength() for e in path) >= 800:
            paths.append(path)
        if len(paths) >= 90:
            break
    if len(paths) < 20:
        raise ValueError('Insufficient connected background traffic routes')
    root = ET.Element('routes')
    ET.SubElement(root, 'vType', id='car', vClass='passenger', sigma='0.5', length='4.5',
                  minGap='2.5', maxSpeed='19.44', speedFactor='normc(1,0.1,0.8,1.2)')
    ET.SubElement(root, 'vType', id='ambulance', vClass='emergency', guiShape='emergency',
                  sigma='0', length='6', minGap='2.5', maxSpeed='19.44', color='1,0.15,0.2')
    ET.SubElement(root, 'route', id='emergency_seed', edges=' '.join(metadata['routes']['chennai_0']))
    for i, path in enumerate(paths):
        ET.SubElement(root, 'route', id=f'background_{i}', edges=' '.join(path))
    vehicles = [(40.0, 'ambulance_chennai', 'ambulance', 'emergency_seed')]
    for i in range(int(PROFILES[profile]*850)):
        vehicles.append((i/PROFILES[profile], f'car_{i}', 'car', f'background_{rng.randrange(len(paths))}'))
    for depart, vid, kind, route in sorted(vehicles):
        ET.SubElement(root, 'vehicle', id=vid, type=kind, route=route, depart=f'{depart:.3f}',
                      departLane='best', departSpeed='0')
    ET.ElementTree(root).write(directory/'traffic.rou.xml', encoding='utf-8', xml_declaration=True)
    cfg = ET.Element('configuration')
    inputs = ET.SubElement(cfg, 'input')
    ET.SubElement(inputs, 'net-file', value=str(NET.resolve()))
    ET.SubElement(inputs, 'route-files', value='traffic.rou.xml')
    processing = ET.SubElement(cfg, 'processing')
    ET.SubElement(processing, 'time-to-teleport', value='-1')
    ET.ElementTree(cfg).write(directory/'run.sumocfg', encoding='utf-8', xml_declaration=True)
    return directory/'run.sumocfg', metadata


class Disruptions:
    """Slow a future edge only when a legal catalogue diversion still exists.

    The planner decides whether the resulting observed costs justify a replan.
    No revision numbers or expected decisions are imposed by this scenario.
    """
    def __init__(self):
        self.next_changes = [90, 210]
        self.active = {}
        self.changes = []

    def update(self, runtime):
        interface = runtime.core.traci
        for edge, (until, speeds) in list(self.active.items()):
            if runtime.now >= until:
                interface.restore_simulated_edge_speed(edge, speeds)
                del self.active[edge]
                runtime._record_evidence('ENVIRONMENT_RESTORED', edge=edge, source='SUMO_SIMULATED')
        if not self.next_changes or runtime.now < self.next_changes[0] or not runtime.active_plan:
            return
        position = interface.route_position(runtime.ambulance_id)
        edge = position['edge']
        if edge.startswith(':'):
            return
        remaining = position['remaining_route']
        candidates = [p[p.index(edge):] for p in runtime.routes.values() if edge in p]
        for target in remaining[4:-1]:
            if target not in self.active and any(target not in p for p in candidates):
                speeds = interface.set_simulated_edge_speed(target, 1.0)
                self.active[target] = (runtime.now+85, speeds)
                self.next_changes.pop(0)
                change = dict(edge=target, speed_limit_mps=1.0, simulation_time=runtime.now,
                              source='SUMO_SIMULATED', reason='Synthetic roadworks speed restriction')
                self.changes.append(change)
                runtime._record_evidence('ENVIRONMENT_CHANGE', **{k:v for k,v in change.items() if k != 'simulation_time'})
                break
