"""Canonical snapshot of the current SUMO simulation state."""

from dataclasses import dataclass, field
from typing import Dict

from citybrain.core.vehicle_state import VehicleState
from citybrain.core.road_state import RoadState


@dataclass
class CityState:
    """
    Canonical representation of the current SUMO simulation state.

    CityState is NOT a second simulator.  It is the current observed
    canonical snapshot built from TraCI observations each simulation step.

    SUMO remains the source of truth.
    """

    simulation_time: float = 0.0
    vehicles: Dict[str, VehicleState] = field(default_factory=dict)
    roads: Dict[str, RoadState] = field(default_factory=dict)

    def update_vehicle(self, vehicle: VehicleState):
        """Add or update a vehicle."""
        self.vehicles[vehicle.vehicle_id] = vehicle

    def remove_vehicle(self, vehicle_id: str):
        """Remove a vehicle that no longer exists in SUMO."""
        self.vehicles.pop(vehicle_id, None)

    def get_vehicle(self, vehicle_id: str):
        """Get a vehicle by ID."""
        return self.vehicles.get(vehicle_id)

    def vehicle_count(self) -> int:
        """Return the number of tracked vehicles."""
        return len(self.vehicles)

    def update_road(self, road: RoadState):
        """Add or update a road."""
        self.roads[road.road_id] = road

    def remove_road(self, road_id: str):
        """Remove a road."""
        self.roads.pop(road_id, None)

    def get_road(self, road_id: str):
        """Get a road by ID."""
        return self.roads.get(road_id)

    def road_count(self) -> int:
        """Return the number of tracked roads."""
        return len(self.roads)

    def set_simulation_time(self, simulation_time: float):
        """Update the canonical simulation time."""
        self.simulation_time = simulation_time