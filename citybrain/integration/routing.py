"""Physical route contracts and bounded candidates from the live SUMO topology."""
from dataclasses import dataclass
import heapq
import math


@dataclass
class RouteValidation:
    valid: bool
    reason: str
    route: list
    deferred: bool = False


def destination_matches(interface, edge, hospital):
    if not isinstance(hospital, dict) or not hospital.get('id'):
        return False
    destination_edge = hospital.get('destination_edge')
    junction = hospital.get('destination_junction', hospital.get('location'))
    if not destination_edge and not junction:
        return False
    return (not destination_edge or edge == destination_edge) and (
        not junction or interface.edge_topology(edge)['to'] == junction)


def validate_destination(hospital):
    return (isinstance(hospital, dict) and bool(hospital.get('id')) and
            bool(hospital.get('destination_edge') or
                 hospital.get('destination_junction') or hospital.get('location')))


def validate_route(interface, vehicle_id, route, hospital=None, position=None):
    route = list(route)
    if not route:
        return RouteValidation(False, 'empty_route', route)
    if any(not isinstance(e, str) or not e or e.startswith(':') for e in route):
        return RouteValidation(False, 'invalid_edge_in_route', route)
    position = position if position is not None else interface.route_position(vehicle_id)
    edge = position['edge']
    if edge.startswith(':'):
        return RouteValidation(False, 'internal_junction_deferred', route, True)
    if not edge or route[0] != edge:
        return RouteValidation(False, 'route_does_not_start_at_current_edge', route)
    if len(set(route)) != len(route):
        return RouteValidation(False, 'cyclic_route_rejected', route)
    # Membership/permissions also apply to single-edge routes.
    if any(not interface.edge_usable(e, vehicle_id) for e in route):
        return RouteValidation(False, 'unknown_or_disallowed_edge', route)
    if any(b not in interface.successors(a, vehicle_id) for a, b in zip(route, route[1:])):
        return RouteValidation(False, 'disconnected_route', route)
    if hospital is not None:
        if not validate_destination(hospital):
            return RouteValidation(False, 'hospital_destination_missing', route)
        if not destination_matches(interface, route[-1], hospital):
            return RouteValidation(False, 'hospital_endpoint_mismatch', route)
    return RouteValidation(True, 'physical_route_valid', route)


def normalize_candidates(interface, vehicle_id, routes, hospital, position):
    candidates, rejected = {}, {}
    edge = position['edge']
    for name, route in routes.items():
        if not isinstance(route, (list, tuple)) or edge not in route:
            rejected[name] = 'current_edge_not_on_candidate'
            continue
        suffix = list(route[route.index(edge):])
        validation = validate_route(interface, vehicle_id, suffix, hospital, position)
        if validation.valid:
            candidates[str(name)] = suffix
        else:
            rejected[str(name)] = validation.reason
    return candidates, rejected


def generate_candidates(interface, vehicle_id, roads, hospital, position, limit=8):
    """Up to limit simple paths, ordered by observed travel cost.

    This is a candidate supplier. The unchanged planner scores and selects them.
    No scenario routes/timestamps are embedded. A fixed expansion budget bounds
    large networks; exhaustion is reported, never called proof of disconnection.
    """
    edge = position['edge']
    if not edge or edge.startswith(':'):
        return {}, False
    def measured_cost(item):
        road = roads.get(item, {})
        value = road.get('travel_time', float('inf'))
        return value if not road.get('blocked') and isinstance(value, (int, float)) and math.isfinite(value) and value > 0 else math.inf
    queue = [(measured_cost(edge), (edge,))]
    found = {}; expansions = 0
    while queue and len(found) < limit and expansions < 20000:
        cost, path = heapq.heappop(queue); expansions += 1
        current = path[-1]
        if not math.isfinite(cost):
            continue
        if destination_matches(interface, current, hospital):
            found[f'topology_{len(found)}'] = list(path)
            continue
        for successor in sorted(interface.successors(current, vehicle_id)):
            if successor not in path:
                weight = measured_cost(successor)
                if math.isfinite(weight):
                    heapq.heappush(queue, (cost + weight, path + (successor,)))
    return found, bool(queue and expansions >= 20000)


def reachable_without_blocked(interface, vehicle_id, roads, hospital, position):
    """Topology reachability ignoring transient infinite costs, respecting blocks."""
    pending = [position['edge']]; visited = set()
    while pending:
        edge = pending.pop()
        if edge in visited or edge.startswith(':') or roads.get(edge, {}).get('blocked'):
            continue
        visited.add(edge)
        if destination_matches(interface, edge, hospital):
            return True
        pending.extend(interface.successors(edge, vehicle_id) - visited)
    return False
