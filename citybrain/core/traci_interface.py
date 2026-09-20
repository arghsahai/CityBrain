"""Core-owned wrapper around SUMO/TraCI operations.

Direct TraCI access stays inside the Core layer.  Planner code,
agent code, and experiment code should not import traci directly
for runtime operations.
"""

from typing import Dict, List, Tuple


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
        return {
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