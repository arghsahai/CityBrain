"""Translate canonical state without collecting measurements or making plans.

Congestion labels (including NO_TRAFFIC and UNKNOWN) and travel times are
preserved. In particular, travel_time=0 may describe an empty road measurement;
it does not necessarily represent a physical traversal cost of zero. Interpreting
these values belongs to the planner/scorer, not this adapter.
"""

from copy import deepcopy


_VEHICLE_FIELDS = ("edge", "speed", "position", "lane", "acceleration")
_ROAD_FIELDS = (
    "road_id", "vehicle_count", "average_speed", "road_length", "speed_limit",
    "lane_count", "occupancy", "travel_time", "congestion",
)


def adapt_city_state(
    city_state,
    *,
    blocked_edges=None,
    road_topology=None,
    ambulances=None,
    hospitals=None,
    routes=None,
    simulation_time=None,
):
    """Return an independent dictionary snapshot for existing agents/planners.

    city_state exposes optional vehicles/roads mappings of IDs to canonical
    objects. This supports both the current vehicle-only CityState and Argh's
    road-bearing version without importing or replacing either implementation.
    Missing collections (or None) yield empty collections. Only present object
    attributes are copied; road_length retains Argh's actual field name.

    Planning context consists of ambulance/hospital record lists, a mapping of
    route IDs to edge lists, optional time, an iterable of known blocked edge
    IDs, and a mapping of edge IDs to topology dictionaries. Only from/to are
    copied from topology. Explicit topology or blockage may introduce a partial
    road record, with no fabricated measurements. Routes remain unchanged even
    when they reference unmeasured roads.

    Unreported blockage is omitted: existing consumers already default missing
    blocked to False. Absence therefore does not assert a measured clear road.
    Emergency objects remain separate inputs to EmergencyPlanner.create_plan.
    No vehicle classification, availability inference, or route validation occurs.
    All returned nested data is defensively copied.
    """
    vehicles = {}
    for vehicle_id, vehicle in (getattr(city_state, "vehicles", None) or {}).items():
        record = {"id": vehicle.vehicle_id}
        record.update({
            name: getattr(vehicle, name)
            for name in _VEHICLE_FIELDS if hasattr(vehicle, name)
        })
        vehicles[vehicle_id] = record

    roads = {}
    for edge_id, road in (getattr(city_state, "roads", None) or {}).items():
        roads[edge_id] = {
            name: getattr(road, name)
            for name in _ROAD_FIELDS if hasattr(road, name)
        }

    for edge_id, topology in (road_topology or {}).items():
        endpoints = {name: topology[name] for name in ("from", "to") if name in topology}
        if endpoints:
            roads.setdefault(edge_id, {}).update(endpoints)

    for edge_id in blocked_edges if blocked_edges is not None else ():
        roads.setdefault(edge_id, {})["blocked"] = True

    return deepcopy({
        "simulation_time": simulation_time,
        "vehicles": vehicles,
        "roads": roads,
        "ambulances": ambulances if ambulances is not None else [],
        "hospitals": hospitals if hospitals is not None else [],
        "routes": routes if routes is not None else {},
    })
