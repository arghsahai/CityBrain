from dataclasses import dataclass, field
from typing import Dict

from citybrain.core.vehicle_state import VehicleState
from citybrain.core.road_state import RoadState


@dataclass
class CityState:
    """
    Central representation of the current simulation state.
    """

    vehicles: Dict[str, VehicleState] = field(default_factory=dict)
    roads: Dict[str, RoadState] = field(default_factory=dict)

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

    def update_road(self, road: RoadState):
        """
        Add or update a road in the city state.
        """
        self.roads[road.road_id] = road

    def remove_road(self, road_id: str):
        """
        Remove a road from the city state.
        """
        self.roads.pop(road_id, None)

    def get_road(self, road_id: str):
        """
        Get a road by its ID.
        """
        return self.roads.get(road_id)

    def road_count(self) -> int:
        """
        Return the number of roads currently tracked.
        """
        return len(self.roads)