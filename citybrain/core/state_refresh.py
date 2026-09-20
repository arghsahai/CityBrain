"""Refresh canonical CityState from SUMO's current simulation step.

Vehicle disappearance semantics
-------------------------------
Vehicle disappearance is NOT automatically arrival.
SUMO teleportation is NOT CityBrain success.

Where TraCI provides lifecycle data, this module distinguishes:
    ARRIVED       vehicle reached its destination
    TELEPORTED    SUMO teleported the vehicle (not a CityBrain success)
    DISAPPEARED   vehicle left the simulation for an unknown reason
"""

from citybrain.core.city_state import CityState
from citybrain.core.vehicle_state import VehicleState
from citybrain.core.traffic_perception import build_road_state


# Reason codes for vehicle removal.
ARRIVED = "ARRIVED"
TELEPORTED = "TELEPORTED"
DISAPPEARED = "DISAPPEARED"


def _detect_blocked_edges(traci):
    """
    Detect roads that are physically blocked by a stopped accident vehicle.

    The detection is based on the live SUMO/TraCI state rather than
    hard-coding a scenario-specific edge such as E7.

    A vehicle is considered a blockage vehicle when:
      - its type is an accident vehicle, and
      - its speed is effectively zero.

    SUMO remains the source of truth.
    """

    blocked_edges = set()

    for vehicle_id in traci.vehicle.getIDList():
        vehicle_type = traci.vehicle.getTypeID(vehicle_id)

        if vehicle_type != "accidentVehicle":
            continue

        speed = traci.vehicle.getSpeed(vehicle_id)

        if speed > 0.1:
            continue

        edge_id = traci.vehicle.getRoadID(vehicle_id)

        if not edge_id:
            continue

        if edge_id.startswith(":"):
            continue

        blocked_edges.add(edge_id)

    return blocked_edges


def _classify_removal(vehicle_id, arrived_ids, teleported_ids):
    """Classify why a vehicle disappeared from SUMO."""

    if vehicle_id in teleported_ids:
        return TELEPORTED

    if vehicle_id in arrived_ids:
        return ARRIVED

    return DISAPPEARED


def refresh_city_state(
    traci,
    city_state: CityState,
    blocked_edges=None,
) -> tuple:
    """
    Refresh the canonical CityState from the current SUMO state.

    If blocked_edges is not supplied, physical accident vehicles are
    detected directly from TraCI.

    Returns:
        (city_state, removals)

        removals is a dict mapping removed vehicle_id to its removal
        reason (ARRIVED, TELEPORTED, DISAPPEARED).
    """

    if blocked_edges is None:
        blocked_edges = _detect_blocked_edges(traci)
    else:
        blocked_edges = set(blocked_edges)

    # ---------------------------------------------------------
    # Simulation time
    # ---------------------------------------------------------

    city_state.set_simulation_time(traci.simulation.getTime())

    # ---------------------------------------------------------
    # Vehicle lifecycle
    # ---------------------------------------------------------

    arrived_ids = set(traci.simulation.getArrivedIDList())
    teleported_ids = set(
        traci.simulation.getStartingTeleportIDList()
    )

    active_vehicle_ids = set(traci.vehicle.getIDList())
    tracked_vehicle_ids = set(city_state.vehicles.keys())

    removals = {}

    # Remove vehicles that have disappeared from SUMO.
    for vehicle_id in tracked_vehicle_ids - active_vehicle_ids:
        reason = _classify_removal(
            vehicle_id, arrived_ids, teleported_ids,
        )
        removals[vehicle_id] = reason
        city_state.remove_vehicle(vehicle_id)

    # Refresh every active vehicle.
    for vehicle_id in active_vehicle_ids:

        edge_id = traci.vehicle.getRoadID(vehicle_id)
        route = list(traci.vehicle.getRoute(vehicle_id))
        route_idx = traci.vehicle.getRouteIndex(vehicle_id)

        vehicle = VehicleState(
            vehicle_id=vehicle_id,
            edge_id=edge_id,
            lane_id=traci.vehicle.getLaneID(vehicle_id),
            speed=traci.vehicle.getSpeed(vehicle_id),
            position=traci.vehicle.getPosition(vehicle_id),
            route=route,
            route_index=route_idx,
            acceleration=traci.vehicle.getAcceleration(
                vehicle_id
            ),
            vehicle_type=traci.vehicle.getTypeID(vehicle_id),
        )

        city_state.update_vehicle(vehicle)

    # ---------------------------------------------------------
    # Roads
    # ---------------------------------------------------------

    active_road_ids = set()

    for road_id in traci.edge.getIDList():

        # Internal SUMO junction edges are not treated as
        # normal CityBrain roads.
        if road_id.startswith(":"):
            continue

        active_road_ids.add(road_id)

        road_state = build_road_state(
            traci=traci,
            road_id=road_id,
            blocked=road_id in blocked_edges,
        )

        city_state.update_road(road_state)

    # Remove roads no longer present in SUMO.
    tracked_road_ids = set(city_state.roads.keys())

    for road_id in tracked_road_ids - active_road_ids:
        city_state.remove_road(road_id)

    return city_state, removals