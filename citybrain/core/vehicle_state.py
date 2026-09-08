from dataclasses import dataclass
from typing import Tuple


@dataclass
class VehicleState:
    """
    Represents the current state of one vehicle
    inside the SUMO simulation.
    """

    vehicle_id: str
    edge: str
    speed: float
    position: Tuple[float, float]
    lane: str
    acceleration: float