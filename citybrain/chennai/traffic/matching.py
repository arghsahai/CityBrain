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


class RoadMatcher:
    def __init__(self, net, *, tolerance=15, ambiguity_margin=3, heading_degrees=35):
        if not (0 < tolerance <= 30 and 0 < ambiguity_margin <= tolerance and 0 < heading_degrees < 90):
            raise ValueError('Invalid matching thresholds')
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
        def result(status,reason,edges=(),confidence=None):
            return replace(observation,matching_status=status,match_reason=reason,
                           matched_sumo_edges=tuple(edges),matching_confidence=confidence)
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
        confidence = max(0,1-max(distances)/self.tolerance)
        return result('MATCHED','All samples agree in heading, distance, progress and directed connectivity',path,confidence)
