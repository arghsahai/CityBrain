from dataclasses import dataclass


@dataclass
class RoadState:
    road_id: str
    vehicle_count: int
    average_speed: float
    road_length: float
    speed_limit: float
    lane_count: int
    occupancy: float
    travel_time: float
    congestion: str