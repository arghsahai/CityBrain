"""Canonical representation of one SUMO vehicle at a point in time."""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class VehicleState:
    """
    Current observed state of one SUMO vehicle.

    SUMO remains the source of truth.  CityBrain does not invent
    vehicle data; every field comes from a TraCI observation.
    """

    vehicle_id: str
    edge_id: str
    lane_id: str
    speed: float
    position: Tuple[float, float]
    route: list = field(default_factory=list)
    route_index: int = 0
    acceleration: float = 0.0
    vehicle_type: str = ""