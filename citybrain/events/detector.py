"""Detect meaningful changes between CityState snapshots.

The detector reports changes.  It does not decide how the
planner should respond.  Only meaningful events are emitted;
tiny speed fluctuations are ignored.
"""

from typing import Dict, List, Optional

from citybrain.core.city_state import CityState
from citybrain.core.state_refresh import ARRIVED, TELEPORTED
from citybrain.events import CityBrainEvent, EventType


class EventDetector:
    """
    Detect meaningful changes between CityState snapshots.

    The detector reports changes. It does not decide how the
    planner should respond.
    """

    def detect(
        self,
        previous_state: CityState,
        current_state: CityState,
        active_routes: Optional[Dict[str, List[str]]] = None,
        removals: Optional[Dict[str, str]] = None,
    ) -> List[CityBrainEvent]:
        """
        Compare previous and current CityState and emit events.

        Parameters
        ----------
        previous_state : CityState
        current_state : CityState
        active_routes : dict mapping vehicle_id → route edge list
            Used to detect route invalidation.
        removals : dict mapping vehicle_id → removal reason
            (ARRIVED, TELEPORTED, DISAPPEARED)
        """

        events = []

        simulation_time = current_state.simulation_time

        # ---------------------------------------------------------
        # Road changes
        # ---------------------------------------------------------

        road_ids = (
            set(previous_state.roads.keys())
            | set(current_state.roads.keys())
        )

        for road_id in road_ids:

            previous_road = previous_state.roads.get(road_id)
            current_road = current_state.roads.get(road_id)

            if previous_road is None or current_road is None:
                continue

            # Road became blocked.
            if (
                not previous_road.blocked
                and current_road.blocked
            ):
                events.append(
                    CityBrainEvent(
                        event_type=EventType.ROAD_BLOCKED,
                        simulation_time=simulation_time,
                        data={"road_id": road_id},
                        entity_id=road_id,
                        reason="road_became_blocked",
                    )
                )

            # Road became unblocked.
            if (
                previous_road.blocked
                and not current_road.blocked
            ):
                events.append(
                    CityBrainEvent(
                        event_type=EventType.ROAD_UNBLOCKED,
                        simulation_time=simulation_time,
                        data={"road_id": road_id},
                        entity_id=road_id,
                        reason="road_became_unblocked",
                    )
                )

            # Congestion category changed.
            if (
                previous_road.congestion
                != current_road.congestion
            ):
                events.append(
                    CityBrainEvent(
                        event_type=EventType.CONGESTION_CHANGED,
                        simulation_time=simulation_time,
                        data={
                            "road_id": road_id,
                            "previous": previous_road.congestion,
                            "current": current_road.congestion,
                        },
                        entity_id=road_id,
                    )
                )

        # ---------------------------------------------------------
        # Active route invalidation
        # ---------------------------------------------------------

        if active_routes:
            for vehicle_id, route in active_routes.items():
                blocked_edges = [
                    edge_id
                    for edge_id in route
                    if (
                        edge_id in current_state.roads
                        and current_state.roads[edge_id].blocked
                    )
                ]

                if blocked_edges:
                    events.append(
                        CityBrainEvent(
                            event_type=EventType.ROUTE_INVALIDATED,
                            simulation_time=simulation_time,
                            data={
                                "vehicle_id": vehicle_id,
                                "route": list(route),
                                "blocked_edges": blocked_edges,
                            },
                            entity_id=vehicle_id,
                            reason="route_edge_blocked",
                        )
                    )

        # ---------------------------------------------------------
        # Vehicle lifecycle
        # ---------------------------------------------------------

        if removals:
            for vehicle_id, reason in removals.items():
                prev_vehicle = previous_state.vehicles.get(
                    vehicle_id
                )

                if reason == ARRIVED:
                    events.append(
                        CityBrainEvent(
                            event_type=EventType.VEHICLE_ARRIVED,
                            simulation_time=simulation_time,
                            data={
                                "vehicle_id": vehicle_id,
                                "vehicle_type": (
                                    prev_vehicle.vehicle_type
                                    if prev_vehicle
                                    else None
                                ),
                            },
                            entity_id=vehicle_id,
                            reason="vehicle_arrived_at_destination",
                        )
                    )
                elif reason == TELEPORTED:
                    events.append(
                        CityBrainEvent(
                            event_type=EventType.VEHICLE_TELEPORTED,
                            simulation_time=simulation_time,
                            data={
                                "vehicle_id": vehicle_id,
                                "vehicle_type": (
                                    prev_vehicle.vehicle_type
                                    if prev_vehicle
                                    else None
                                ),
                            },
                            entity_id=vehicle_id,
                            reason="sumo_teleported_vehicle",
                        )
                    )

        # ---------------------------------------------------------
        # Ambulance changes
        # ---------------------------------------------------------

        vehicle_ids = (
            set(previous_state.vehicles.keys())
            & set(current_state.vehicles.keys())
        )

        for vehicle_id in vehicle_ids:

            previous_vehicle = previous_state.vehicles[vehicle_id]
            current_vehicle = current_state.vehicles[vehicle_id]

            if current_vehicle.vehicle_type != "ambulance":
                continue

            if (
                previous_vehicle.edge_id != current_vehicle.edge_id
                or previous_vehicle.speed != current_vehicle.speed
            ):
                events.append(
                    CityBrainEvent(
                        event_type=EventType.AMBULANCE_STATE_CHANGED,
                        simulation_time=simulation_time,
                        data={
                            "vehicle_id": vehicle_id,
                            "previous_edge": previous_vehicle.edge_id,
                            "current_edge": current_vehicle.edge_id,
                            "previous_speed": previous_vehicle.speed,
                            "current_speed": current_vehicle.speed,
                        },
                        entity_id=vehicle_id,
                    )
                )

        return events