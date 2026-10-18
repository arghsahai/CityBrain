"""Core-owned wrapper around SUMO/TraCI operations.

Direct TraCI access stays inside the Core layer.  Planner code,
agent code, and experiment code should not import traci directly
for runtime operations.
"""

from typing import Dict, List, Tuple
import math


class TraCIInterface:
    """
    Small Core-owned wrapper around SUMO/TraCI operations.

    Direct TraCI access stays inside the Core layer.
    """

    def __init__(self, traci):
        self.traci = traci

    # ---------------------------------------------------------
    # Simulation
    # ---------------------------------------------------------

    def simulation_time(self) -> float:
        return self.traci.simulation.getTime()

    def step(self) -> None:
        self.traci.simulationStep()

    def arrived_vehicles(self) -> List[str]:
        """Vehicle IDs that arrived at their destination this step."""
        return list(self.traci.simulation.getArrivedIDList())

    def teleported_vehicles(self) -> List[str]:
        """Vehicle IDs that were teleported by SUMO this step."""
        return list(
            self.traci.simulation.getStartingTeleportIDList()
        )

    # ---------------------------------------------------------
    # Vehicles
    # ---------------------------------------------------------

    def vehicle_ids(self) -> List[str]:
        return list(self.traci.vehicle.getIDList())

    def vehicle_exists(self, vehicle_id: str) -> bool:
        """Check whether a vehicle is currently active in SUMO."""
        return vehicle_id in self.traci.vehicle.getIDList()

    def vehicle_state(self, vehicle_id: str) -> dict:
        return {
            "vehicle_id": vehicle_id,
            "edge_id": self.traci.vehicle.getRoadID(vehicle_id),
            "lane_id": self.traci.vehicle.getLaneID(vehicle_id),
            "speed": self.traci.vehicle.getSpeed(vehicle_id),
            "position": self.traci.vehicle.getPosition(vehicle_id),
            "acceleration": self.traci.vehicle.getAcceleration(
                vehicle_id
            ),
            "vehicle_type": self.traci.vehicle.getTypeID(
                vehicle_id
            ),
        }

    def current_route(self, vehicle_id: str) -> List[str]:
        return list(self.traci.vehicle.getRoute(vehicle_id))

    def route_index(self, vehicle_id: str) -> int:
        return self.traci.vehicle.getRouteIndex(vehicle_id)

    def current_route_suffix(self, vehicle_id: str) -> List[str]:
        """Return the remaining (not-yet-traversed) portion of the route."""
        route = self.traci.vehicle.getRoute(vehicle_id)
        index = self.traci.vehicle.getRouteIndex(vehicle_id)
        return list(route[index:])

    def apply_route(
        self,
        vehicle_id: str,
        route: List[str],
    ) -> None:
        self.traci.vehicle.setRoute(vehicle_id, route)

    # ---------------------------------------------------------
    # Roads / Edges
    # ---------------------------------------------------------

    def road_ids(self) -> List[str]:
        return list(self.traci.edge.getIDList())

    def edge_topology(self, edge_id: str) -> Dict[str, str]:
        """Return from/to junction IDs for a SUMO edge."""
        return {
            "from": self.traci.edge.getFromJunction(edge_id),
            "to": self.traci.edge.getToJunction(edge_id),
        }

    # ---------------------------------------------------------
    # Traffic signals
    # ---------------------------------------------------------

    def signal_ids(self) -> List[str]:
        return list(self.traci.trafficlight.getIDList())

    def signal_state(self, signal_id: str) -> dict:
        state = {
            "signal_id": signal_id,
            "phase": self.traci.trafficlight.getPhase(
                signal_id
            ),
            "state": self.traci.trafficlight.getRedYellowGreenState(
                signal_id
            ),
            "phase_duration": self.traci.trafficlight.getPhaseDuration(
                signal_id
            ),
        }
        # SUMO exposes the programmed next switch. Keep timing unavailable when
        # the backend cannot provide a finite, internally consistent value.
        try:
            now = float(self.traci.simulation.getTime())
            next_switch = float(self.traci.trafficlight.getNextSwitch(signal_id))
            duration = float(state['phase_duration'])
            remaining = next_switch - now
            if all(map(math.isfinite, (now, next_switch, duration))) and duration >= 0 and remaining >= 0:
                elapsed = duration - remaining
                state.update(phase_start_time=now-elapsed if elapsed >= 0 else None,
                             phase_elapsed_seconds=elapsed if elapsed >= 0 else None,
                             remaining_phase_seconds=remaining)
            else:
                state.update(phase_start_time=None, phase_elapsed_seconds=None,
                             remaining_phase_seconds=None)
        except (AttributeError, TypeError, ValueError, OverflowError):
            state.update(phase_start_time=None, phase_elapsed_seconds=None,
                         remaining_phase_seconds=None)
        return state

    def geographic_observations(self) -> dict:
        """Read-only geographical observations on Core's existing connection.

        Callers isolate failures at their telemetry boundary. No subscriptions,
        simulation steps, vehicle writes, or additional TraCI clients are used.
        """
        timestamp = self.simulation_time()
        vehicles = []
        for vehicle_id in self.vehicle_ids():
            state = self.vehicle_state(vehicle_id)
            lon, lat = self.traci.simulation.convertGeo(*state['position'])
            vehicles.append(dict(id=vehicle_id, category=state['vehicle_type'],
                longitude=lon, latitude=lat, speed=state['speed'],
                heading=self.traci.vehicle.getAngle(vehicle_id), road=state['edge_id'],
                simulation_time=timestamp, source='SUMO_SIMULATED'))
        signals = []
        for signal_id in self.signal_ids():
            # Joined junction IDs need not be available through junction.getPosition.
            lanes = self.traci.trafficlight.getControlledLanes(signal_id)
            points = [self.traci.lane.getShape(lane)[-1] for lane in set(lanes)]
            if not points:
                continue
            point = (sum(p[0] for p in points)/len(points), sum(p[1] for p in points)/len(points))
            lon, lat = self.traci.simulation.convertGeo(*point)
            signals.append(dict(**self.signal_state(signal_id), longitude=lon, latitude=lat,
                                simulation_time=timestamp, source='SUMO_SIMULATED'))
        return dict(vehicles=vehicles, signals=signals, simulation_time=timestamp, source='SUMO_SIMULATED')

    def set_simulated_edge_speed(self, edge_id: str, speed: float) -> list:
        """Explicit pilot scenario action, unrelated to advisory signal control."""
        if speed <= 0:
            raise ValueError('speed must be positive')
        previous = []
        for i in range(self.traci.edge.getLaneNumber(edge_id)):
            lane = f'{edge_id}_{i}'
            previous.append(self.traci.lane.getMaxSpeed(lane))
            self.traci.lane.setMaxSpeed(lane, speed)
        return previous

    def restore_simulated_edge_speed(self, edge_id: str, speeds: list) -> None:
        for i, speed in enumerate(speeds):
            self.traci.lane.setMaxSpeed(f'{edge_id}_{i}', speed)

    def request_signal_priority(
        self,
        signal_id: str,
        phase: int,
    ) -> None:
        """
        Interface for future signal-priority actions.

        The Core exposes the TraCI action, but does not implement
        a green-corridor policy.  Physical signal control is
        advisory-only in the current architecture.
        """
        self.traci.trafficlight.setPhase(signal_id, phase)
    def route_position(self, vehicle_id):
        route = list(self.traci.vehicle.getRoute(vehicle_id))
        index = self.traci.vehicle.getRouteIndex(vehicle_id)
        edge = self.traci.vehicle.getRoadID(vehicle_id)
        if not isinstance(index, int) or index < 0 or index >= len(route):
            raise ValueError('invalid_route_index')
        if not edge.startswith(':') and route[index] != edge:
            raise ValueError('physical_edge_route_index_mismatch')
        return {'edge': edge, 'route_index': index, 'route': route,
                'remaining_route': route[index:]}

    def _allowed_lane(self, lane_id, vehicle_class):
        allowed = self.traci.lane.getAllowed(lane_id)
        denied = self.traci.lane.getDisallowed(lane_id)
        return (not allowed or vehicle_class in allowed) and vehicle_class not in denied

    def edge_usable(self, edge_id, vehicle_id):
        vehicle_class = self.traci.vehicle.getVehicleClass(vehicle_id)
        key = (edge_id, vehicle_class)
        cache = self.__dict__.setdefault('_usable_cache', {})
        if key not in cache:
            if edge_id.startswith(':') or edge_id not in self.road_ids():
                cache[key] = False
            else:
                cache[key] = any(self._allowed_lane(f'{edge_id}_{i}', vehicle_class)
                                 for i in range(self.traci.edge.getLaneNumber(edge_id)))
        return cache[key]

    def successors(self, edge_id, vehicle_id):
        vehicle_class = self.traci.vehicle.getVehicleClass(vehicle_id)
        key = (edge_id, vehicle_class)
        cache = self.__dict__.setdefault('_successor_cache', {})
        if key not in cache:
            following = set()
            if self.edge_usable(edge_id, vehicle_id):
                for i in range(self.traci.edge.getLaneNumber(edge_id)):
                    lane = f'{edge_id}_{i}'
                    if self._allowed_lane(lane, vehicle_class):
                        for link in self.traci.lane.getLinks(lane):
                            target = link[0]
                            if self._allowed_lane(target, vehicle_class):
                                following.add(self.traci.lane.getEdgeID(target))
            cache[key] = following
        return set(cache[key])
