"""Conservative directed polyline matching against a read-only SUMO network.

Densified geometry, local tangent agreement, distance margins, monotonic progress
and actual edge connectivity are all required. Close parallel alternatives are
rejected, not resolved using an arbitrary ID or provider-to-SUMO lookup table.
"""
from dataclasses import replace
import math


def segments(points):
    offset = 0
    for a,b in zip(points,points[1:]):
        dx,dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx,dy)
        if length > .01:
            yield a,b,length,offset,(dx/length,dy/length)
            offset += length


def projection(point, a,b,length):
    dx,dy = b[0]-a[0],b[1]-a[1]
    ratio = max(0,min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dy)/(length*length)))
    return math.hypot(point[0]-a[0]-ratio*dx,point[1]-a[1]-ratio*dy), ratio*length


def overlap_interval(start, end, road_start, road_length, direction, tolerance):
    """Clip a provider leg to a finite road strip, without endpoint clamping.

    Both the longitudinal projection and perpendicular distance are linear in
    the provider-leg parameter. Intersect their valid intervals with [0, 1].
    A road endpoint's circular distance buffer is deliberately not coverage.
    """
    dx,dy = end[0]-start[0],end[1]-start[1]
    x,y = start[0]-road_start[0],start[1]-road_start[1]
    ux,uy = direction
    lower,upper = 0.0,1.0
    for origin,delta,minimum,maximum in (
            (x*ux+y*uy,dx*ux+dy*uy,0,road_length),
            (x*(-uy)+y*ux,dx*(-uy)+dy*ux,-tolerance,tolerance)):
        if abs(delta) < 1e-12:
            if origin < minimum-1e-9 or origin > maximum+1e-9:
                return None
        else:
            first,last = sorted(((minimum-origin)/delta,(maximum-origin)/delta))
            lower,upper = max(lower,first),min(upper,last)
            if upper <= lower:
                return None
    return lower,upper


class RoadMatcher:
    def __init__(self, net, *, tolerance=15, ambiguity_margin=3, heading_degrees=35,
                 minimum_coverage=0.95):
        if not (0 < tolerance <= 30 and 0 < ambiguity_margin <= tolerance and 0 < heading_degrees < 90):
            raise ValueError('Invalid matching thresholds')
        if isinstance(minimum_coverage,bool) or not math.isfinite(minimum_coverage) or not 0 < minimum_coverage <= 1:
            raise ValueError('Minimum coverage must be within (0, 1]')
        self.minimum_coverage = minimum_coverage
        self.net, self.tolerance, self.margin = net,tolerance,ambiguity_margin
        self.cosine = math.cos(math.radians(heading_degrees))
        self.edges, self.grid = {}, {}
        self.cell_size = 50
        for edge in net.getEdges():
            if edge.getID().startswith(':') or not edge.allows('passenger'):
                continue
            parts = list(segments(edge.getShape()))
            self.edges[edge.getID()] = (parts,{e.getID() for e in edge.getOutgoing()})
            for part in parts:
                a,b,*_ = part
                for x in range(math.floor((min(a[0],b[0])-tolerance)/self.cell_size),math.floor((max(a[0],b[0])+tolerance)/self.cell_size)+1):
                    for y in range(math.floor((min(a[1],b[1])-tolerance)/self.cell_size),math.floor((max(a[1],b[1])+tolerance)/self.cell_size)+1):
                        self.grid.setdefault((x,y),[]).append((edge.getID(),part))

    def match(self, observation):
        def result(status,reason,edges=(),confidence=None,coverage=None):
            return replace(observation,matching_status=status,match_reason=reason,
                           matched_sumo_edges=tuple(edges),matching_confidence=confidence,
                           matching_coverage=coverage)
        if len(observation.road_geometry) < 2 or observation.direction != 'FORWARD':
            return result('INSUFFICIENT_DATA','Requires a directed polyline, not a point or unverified direction')
        points = [self.net.convertLonLat2XY(*p) for p in observation.road_geometry]
        parts = list(segments(points))
        total = sum(p[2] for p in parts)
        if total < 15:
            return result('INSUFFICIENT_DATA','Directed segment shorter than 15 m')
        samples = []
        for a,b,length,offset,tangent in parts:
            count = max(1,math.ceil(length/10))
            for index in range(count):
                ratio = (index+.5)/count
                samples.append(((a[0]+(b[0]-a[0])*ratio,a[1]+(b[1]-a[1])*ratio),tangent))
        if len(samples) > 4000:
            return result('INSUFFICIENT_DATA','Segment exceeds matching sample budget')
        path, distances, last_progress = [], [], None
        for point,tangent in samples:
            best_by_edge = {}
            cell = math.floor(point[0]/self.cell_size),math.floor(point[1]/self.cell_size)
            for edge_id,(a,b,length,offset,direction) in self.grid.get(cell,()):
                if tangent[0]*direction[0]+tangent[1]*direction[1] < self.cosine:
                    continue
                distance,progress = projection(point,a,b,length)
                if distance <= self.tolerance and (edge_id not in best_by_edge or distance < best_by_edge[edge_id][0]):
                    best_by_edge[edge_id] = distance,offset+progress
            candidates = [(distance,edge_id,progress) for edge_id,(distance,progress) in best_by_edge.items()]
            candidates.sort()
            if not candidates:
                return result('UNMATCHED','A geometry sample has no nearby heading-consistent road')
            distance,edge_id,progress = candidates[0]
            for other_distance,other_id,other_progress in candidates[1:]:
                if other_distance-distance >= self.margin:
                    break
                edge_length = sum(part[2] for part in self.edges[edge_id][0])
                other_length = sum(part[2] for part in self.edges[other_id][0])
                # Connectivity resolves a tie only near an actual end/start
                # transition. Parallel connected roads remain ambiguous mid-edge.
                connected = ((other_id in self.edges[edge_id][1] and progress >= edge_length-10 and other_progress <= 10) or
                             (edge_id in self.edges[other_id][1] and other_progress >= other_length-10 and progress <= 10))
                if not connected:
                    return result('AMBIGUOUS','Nearby parallel/intersection alternatives lack a clear distance margin')
            if path and edge_id == path[-1]:
                if progress+2 < last_progress:
                    return result('AMBIGUOUS','Geometry reverses progress along a road')
            elif path:
                if edge_id in path or edge_id not in self.edges[path[-1]][1]:
                    return result('UNMATCHED','Matched fragments do not form a directed connected path')
                path.append(edge_id)
            else:
                path.append(edge_id)
            last_progress = progress
            distances.append(distance)
        # Confidence is a geometric heuristic, not a calibrated probability.
        # Validate extent on the accepted connected path, not on arbitrary nearby
        # roads. Merge intervals so curved/overlapping road parts cannot double
        # count provider length. A provider subsegment inside a longer road is
        # fully covered; a longer provider segment over a short road is not.
        covered = 0.0
        for a,b,length,_,tangent in parts:
            intervals = []
            for edge_id in path:
                for road_start,_,road_length,_,direction in self.edges[edge_id][0]:
                    if tangent[0]*direction[0]+tangent[1]*direction[1] < self.cosine:
                        continue
                    interval = overlap_interval(a,b,road_start,road_length,direction,self.tolerance)
                    if interval is not None:
                        intervals.append(interval)
            end = 0.0
            for first,last in sorted(intervals):
                covered += max(0,last-max(first,end))*length
                end = max(end,last)
        coverage = min(1.0,covered/total)
        if coverage+1e-9 < self.minimum_coverage:
            return result('UNMATCHED',
                f'Insufficient longitudinal coverage: {covered:.3f}/{total:.3f} m '
                f'({coverage:.1%}); requires {self.minimum_coverage:.1%}',coverage=coverage)
        confidence = max(0,1-max(distances)/self.tolerance)
        return result('MATCHED','Heading, distance, progress, directed connectivity and '
                      f'longitudinal coverage verified ({coverage:.1%})',path,confidence,coverage)
