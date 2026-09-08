from dataclasses import dataclass, field
from typing import Dict

from citybrain.core.vehicle_state import VehicleState


@dataclass
class CityState:
    """
    Central representation of the current simulation state.
    """

    vehicles: Dict[str, VehicleState] = field(default_factory=dict)

    def update_vehicle(self, vehicle: VehicleState):
        """
        Add or update a vehicle in the city state.
        """
        self.vehicles[vehicle.vehicle_id] = vehicle

    def remove_vehicle(self, vehicle_id: str):
        """
        Remove a vehicle from the city state.
        """
        self.vehicles.pop(vehicle_id, None)

    def get_vehicle(self, vehicle_id: str):
        """
        Get a vehicle by its ID.
        """
        return self.vehicles.get(vehicle_id)

    def vehicle_count(self) -> int:
        """
        Return the number of vehicles currently tracked.
        """
        return len(self.vehicles)