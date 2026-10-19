"""Directed pilot graph, conservative pin matching and partial-edge search.

Road geometry/speeds are retained OSM/SUMO import data, not current traffic.
Passenger-class access is a prototype proxy, not verified ambulance access.
"""
import heapq
import math
from types import SimpleNamespace
from citybrain.chennai.network import BOUNDS, read_network
from citybrain.chennai.traffic.matching import segments, projection
from citybrain.planner.route_scorer import RouteScorer
from citybrain.planner.plan_validator import PlanValidator


def route_provenance(components):
    total=sum(c['distance_m'] for c in components)
    observed=sum(c['distance_m'] for c in components if c['source']!='ESTIMATED_FREE_FLOW')
    return dict(observed_distance_m=observed,estimated_distance_m=max(0,total-observed),
        observed_fraction=observed/total if total else 0,
        estimated_fraction=(total-observed)/total if total else 0,
        source_times=sorted({c['source_time'] for c in components if c.get('source_time')}),
        sources=sorted({c['source'] for c in components}),
        label='TRAFFIC_ASSISTED_ESTIMATE' if observed else 'ESTIMATED_FREE_FLOW',
        field_validated=False)


class LiveError(ValueError):
    def __init__(self, code, detail=None):
        self.code, self.detail = code, detail
        super().__init__(code)


def coordinate(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise LiveError('INVALID_COORDINATES')
    if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) for v in value):
        raise LiveError('INVALID_COORDINATES')
    lon, lat = value
    if not -180 <= lon <= 180 or not -90 <= lat <= 90:
        raise LiveError('INVALID_COORDINATES')
    return [float(lon), float(lat)]


class PilotGraph:
    def __init__(self):
        self.net = read_network()  # Data parser only: never starts SUMO.
        self.edges, self.grid = {}, {}
        for edge in self.net.getEdges():
            coords = [list(self.net.convertXY2LonLat(*p)) for p in edge.getShape()]
            if not edge.allows('passenger') or len(coords) < 2 or not all(self.in_bounds(p) for p in coords):
                continue
            parts = list(segments(edge.getShape()))
            if not parts or edge.getSpeed() <= 0:
                continue
            length = sum(p[2] for p in parts)
            self.edges[edge.getID()] = dict(id=edge.getID(), coordinates=coords, parts=parts,
                geometry_length=length, length=edge.getLength(), speed=edge.getSpeed(),
                name=edge.getName() or edge.getID(), to=edge.getToNode().getID())
            for part in parts:
                a, b = part[:2]
                for x in range(math.floor((min(a[0],b[0])-25)/50), math.floor((max(a[0],b[0])+25)/50)+1):
                    for y in range(math.floor((min(a[1],b[1])-25)/50), math.floor((max(a[1],b[1])+25)/50)+1):
                        self.grid.setdefault((x,y), []).append((edge.getID(), part))
        self.next = {eid: sorted(e.getID() for e, cs in self.net.getEdge(eid).getOutgoing().items()
            if e.getID() in self.edges and any(c.allows('passenger') for c in cs)) for eid in self.edges}

    @staticmethod
    def in_bounds(p):
        return BOUNDS[0] <= p[0] <= BOUNDS[2] and BOUNDS[1] <= p[1] <= BOUNDS[3]

    def snap(self, point, selected_edge=None):
        point = coordinate(point)
        if not self.in_bounds(point):
            raise LiveError('OUTSIDE_ROUTING_PILOT', list(BOUNDS))
        xy = self.net.convertLonLat2XY(*point)
        candidates = {}
        for eid, part in self.grid.get((math.floor(xy[0]/50), math.floor(xy[1]/50)), []):
            a,b,length,offset,_ = part
            distance, along = projection(xy,a,b,length)
            if distance <= 25 and (eid not in candidates or distance < candidates[eid]['distance_m']):
                fraction = (offset+along)/self.edges[eid]['geometry_length']
                candidates[eid] = dict(edge=eid, fraction=fraction, distance_m=distance,
                    coordinates=self.point_at(eid, fraction), direction='ALONG_DIRECTED_EDGE', source='USER_SELECTED',
                    confidence='USER_CONFIRMED_DIRECTION' if selected_edge else 'GEOMETRY_ONLY')
        ordered = sorted(candidates.values(), key=lambda p:(p['distance_m'],p['edge']))
        if not ordered:
            raise LiveError('OFF_ROAD', 'No passenger-access road within 25 metres')
        plausible = [c for c in ordered if c['distance_m'] <= ordered[0]['distance_m']+3]
        if selected_edge:
            if selected_edge not in {p['edge'] for p in plausible}:
                raise LiveError('INVALID_DIRECTED_EDGE_CHOICE', plausible[:8])
            return candidates[selected_edge]
        if len(plausible)>1:
            raise LiveError('AMBIGUOUS_DIRECTION_SELECT_EDGE', plausible[:8])
        return ordered[0]

    def point_at(self, eid, fraction):
        edge = self.edges[eid]
        distance = max(0,min(1,fraction))*edge['geometry_length']
        for a,b,length,offset,_ in edge['parts']:
            if distance <= offset+length+1e-7:
                t = max(0,min(1,(distance-offset)/length))
                return list(self.net.convertXY2LonLat(a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])))
        return edge['coordinates'][-1]

    def clipped(self, eid, lower, upper):
        edge = self.edges[eid]
        points = [self.point_at(eid,lower)]
        for _,b,length,offset,_ in edge['parts']:
            if lower*edge['geometry_length'] < offset+length < upper*edge['geometry_length']:
                points.append(list(self.net.convertXY2LonLat(*b)))
        points.append(self.point_at(eid,upper))
        return points

    def route(self, start, end, costs=None):
        costs = costs or {}
        def seconds(eid):
            e = self.edges[eid]
            row = costs.get(eid,{})
            value = row.get('seconds',e['length']/e['speed'])
            if row.get('blocked') or not isinstance(value,(float,int)) or not math.isfinite(value) or value <= 0:
                return math.inf
            return value
        first, target = start['edge'],end['edge']
        if first not in self.edges or target not in self.edges or not math.isfinite(seconds(first)):
            raise LiveError('UNREACHABLE')
        sf,tf = start['fraction'],end['fraction']
        if first == target and tf >= sf:
            path = [first]
        else:
            # Virtual start permits a legal cycle when destination is behind on
            # the same one-way edge. Never run that edge backwards.
            queue = [(seconds(first)*(1-sf), first, (first,))]
            visited = set()
            path = None
            while queue:
                cost,eid,prefix = heapq.heappop(queue)
                if eid == target and len(prefix)>1:
                    path = list(prefix)
                    break
                key = (eid, len(prefix)==1)
                if key in visited:
                    continue
                visited.add(key)
                for nxt in self.next[eid]:
                    weight = seconds(nxt)*(tf if nxt==target else 1)
                    if math.isfinite(weight):
                        heapq.heappush(queue,(cost+weight,nxt,prefix+(nxt,)))
            if path is None:
                raise LiveError('UNREACHABLE')
        if any(b not in self.next[a] for a,b in zip(path,path[1:])):
            raise LiveError('DISCONNECTED_ROUTE')
        components, rendered, total = [], [], 0.0
        for i,eid in enumerate(path):
            lo,hi = (sf if i==0 else 0), (tf if i==len(path)-1 else 1)
            fraction = max(0,hi-lo)
            row = costs.get(eid,{})
            seconds_used = seconds(eid)*fraction
            component = dict(edge=eid,seconds=seconds_used,source=row.get('source','ESTIMATED_FREE_FLOW'),
                freshness=row.get('freshness','UNKNOWN'),source_time=row.get('source_time'),
                observation_id=row.get('observation_id'),coverage=row.get('coverage'),fraction=fraction,
                distance_m=self.edges[eid]['length']*fraction)
            components.append(component)
            rendered.append(dict(edge=eid,coordinates=self.clipped(eid,lo,hi)))
            total += seconds_used
        # Reuse scorer/validator; partial zero-length arrivals need a small
        # validation epsilon only, never an invented ETA measurement.
        state = {'roads':{str(i):dict(travel_time=max(c['seconds'],1e-6),congestion='UNKNOWN',blocked=False)
                          for i,c in enumerate(components)}}
        keys = list(state['roads'])
        scored = RouteScorer().explain_score(keys,state)
        valid = PlanValidator().validate_structured(SimpleNamespace(route=keys),state)
        if not scored.usable or not valid.valid:
            raise LiveError('INVALID_ROUTE_COST')
        return dict(route=path,geometry=rendered,eta_seconds=total,
            eta_label='ESTIMATE — NOT FIELD VALIDATED',components=components,eta_provenance=route_provenance(components),
            estimated_edges=sum(c['source']=='ESTIMATED_FREE_FLOW' for c in components),
            observed_edges=sum(c['source']!='ESTIMATED_FREE_FLOW' for c in components),
            connectivity='LEGAL_PASSENGER_CONNECTIONS',execution='RECOMMENDATION_ONLY',
            assumptions='Imported speed limits; no intersection delay on unobserved edges; road-level arrival only')

    def geography(self):
        return dict(bounds=list(BOUNDS), roads={eid:{k:e[k] for k in ('coordinates','name')} for eid,e in self.edges.items()},
                    attribution='© OpenStreetMap contributors · ODbL 1.0',
                    display_coverage='Chennai-wide globe / optional OSM tiles',routing_coverage='BOUNDED PILOT ONLY')
