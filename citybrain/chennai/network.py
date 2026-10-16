"""Read and validate the real OSM network, and derive network-specific routes."""
import heapq
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import sumolib

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / 'simulation/chennai'
NET = PILOT / 'network/chennai.net.xml'
BOUNDS = (80.132, 12.823, 80.174, 12.863)


def read_network():
    if not NET.exists():
        raise FileNotFoundError('Run python -m citybrain.chennai.build first')
    return sumolib.net.readNet(str(NET))


def shortest(net, start, end, excluded=()):
    """Dijkstra over legal SUMO connections; never infer a turn from proximity."""
    queue = [(0, start, ())]
    visited = set()
    excluded = set(excluded)
    while queue:
        cost, edge_id, prefix = heapq.heappop(queue)
        if edge_id in visited or edge_id in excluded:
            continue
        visited.add(edge_id)
        path = prefix + (edge_id,)
        edge = net.getEdge(edge_id)
        if edge_id == end:
            return list(path)
        for successor, connections in edge.getOutgoing().items():
            if successor.allows('passenger') and any(c.allows('passenger') for c in connections):
                heapq.heappush(queue, (cost + successor.getLength()/successor.getSpeed(),
                                       successor.getID(), path))
    return None


def alternatives(net, start, end, limit=12):
    first = shortest(net, start, end)
    if not first:
        return {}
    found = [first]
    # Leave out each individual interior edge to find genuinely distinct paths.
    for edge in first[1:-1]:
        path = shortest(net, start, end, [edge])
        if path and path not in found:
            found.append(path)
    # Sample diversions across the full journey, rather than only near dispatch.
    if len(found) > limit:
        pool = found[1:]
        chosen = [first]
        while pool and len(chosen) < limit:
            best = max(pool, key=lambda p: min(len(set(p)^set(q)) for q in chosen))
            chosen.append(best)
            pool.remove(best)
        found = chosen
    return {f'chennai_{i}': p for i, p in enumerate(found)}


def nearby(net, lon, lat, radius=250):
    x, y = net.convertLonLat2XY(lon, lat)
    return sorted(((e, d) for e, d in net.getNeighboringEdges(x, y, radius)
                   if e.allows('passenger')), key=lambda item: (item[1], item[0].getID()))


def geography(net):
    osm = ET.parse(PILOT/'network/chennai.osm.xml').getroot()
    nodes = {n.get('id'): [float(n.get('lon')), float(n.get('lat'))] for n in osm.findall('node')}
    buildings = []
    for w in osm.findall('way'):
        tags = {t.get('k'): t.get('v') for t in w.findall('tag')}
        if 'building' not in tags:
            continue
        points = [nodes[nd.get('ref')] for nd in w.findall('nd') if nd.get('ref') in nodes]
        if len(points) >= 4 and all(BOUNDS[0] <= p[0] <= BOUNDS[2] and BOUNDS[1] <= p[1] <= BOUNDS[3] for p in points):
            try:
                height = float(tags['height'].removesuffix(' m')) if 'height' in tags else float(tags['building:levels'])*3
                height_source = 'OSM height' if 'height' in tags else 'ESTIMATED from OSM levels'
            except (KeyError, ValueError):
                height, height_source = 6, 'ESTIMATED visualization height'
            buildings.append(dict(id=w.get('id'), coordinates=points, height=height,
                                  height_source=height_source, name=tags.get('name')))
    return dict(bounds=BOUNDS, center=[80.154, 12.8408], buildings=buildings,
                roads={e.getID(): dict(coordinates=[net.convertXY2LonLat(*p) for p in e.getShape()],
                                      name=e.getName(), classification=e.getType()) for e in net.getEdges()},
                attribution='© OpenStreetMap contributors · ODbL 1.0',
                terrain='WGS84 ellipsoid; terrain elevations unavailable',
                signals='Synthetic SUMO programs at actual OSM junctions; real signal locations unverified')


def prepare_metadata():
    net = read_network()
    start = nearby(net, 80.170, 12.829)[0][0].getID()
    osm = ET.parse(PILOT/'network/chennai.osm.xml').getroot()
    hospitals = []
    for node in osm.findall('node'):
        tags = {t.get('k'): t.get('v') for t in node.findall('tag')}
        if tags.get('amenity') != 'hospital':
            continue
        lon, lat = float(node.get('lon')), float(node.get('lat'))
        for edge, distance in nearby(net, lon, lat):
            path = shortest(net, start, edge.getID())
            if path:
                hospitals.append(dict(id='osm_'+node.get('id'), name=tags.get('name', 'Unnamed hospital'),
                    longitude=lon, latitude=lat, destination_edge=edge.getID(),
                    road_access_distance_m=round(distance, 2), road_access='Reachable road endpoint; final driveway unverified',
                    location_source='https://www.openstreetmap.org/node/'+node.get('id'),
                    icu_available=True, availability_source='SIMULATED; no clinical capacity claim',
                    emergency_services='UNAVAILABLE — not verified'))
                break
    hospital = next(h for h in hospitals if 'Tagore' in h['name'])
    routes = alternatives(net, start, hospital['destination_edge'])
    if len(routes) < 2:
        raise ValueError('Study area lacks verified alternate ambulance routes')
    for path in routes.values():
        assert len(path) == len(set(path))
        assert all(b in [e.getID() for e in net.getEdge(a).getOutgoing()] for a, b in zip(path, path[1:]))
    data = dict(origin_edge=start, hospital=hospital, hospitals=hospitals, routes=routes,
                route_lengths_m={key: round(sum(net.getEdge(e).getLength() for e in path), 2) for key, path in routes.items()},
                edge_count=len(net.getEdges()), signal_count=len(net.getTrafficLights()))
    (PILOT/'network/metadata.json').write_text(json.dumps(data, indent=2)+'\n')
    (PILOT/'network/geography.json').write_text(json.dumps(geography(net))+'\n')
    return data
