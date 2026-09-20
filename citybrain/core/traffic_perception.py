"""TraCI perception boundary: raw SUMO data → canonical RoadState.

SUMO remains the source of truth.  This module reads TraCI
measurements and converts them into the canonical RoadState model
without making planning decisions.

Travel-time semantics
---------------------
EMPTY ROAD (vehicle_count == 0):
    Free-flow estimate: road_length / speed_limit.
    Congestion label: NO_TRAFFIC (aligns with RouteScorer).

FREE-FLOW / CONGESTED ROAD:
    road_length / average_speed using observed traffic.

STOPPED ROAD (vehicles present but average_speed ≈ 0):
    travel_time = infinity.

BLOCKED ROAD:
    travel_time = infinity.

INVALID MEASUREMENT (road_length ≤ 0 or speed_limit ≤ 0):
    travel_time = infinity.
"""

from citybrain.core.road_state import (
    BLOCKED,
    EMPTY,
    MEASURED,
    UNKNOWN,
    RoadState,
)


def calculate_congestion(
    average_speed: float,
    speed_limit: float,
    vehicle_count: int,
) -> str:
    """
    Convert observed road speed into a congestion label.

    Empty roads use NO_TRAFFIC rather than LOW so that
    Subhashini's RouteScorer can apply its free-flow estimate
    path when travel_time is zero on a genuinely empty edge.

    Congestion thresholds use speed ratio:
        < 0.30 = HIGH
        < 0.60 = MEDIUM
        otherwise LOW

    Empty road = NO_TRAFFIC.
    """

    if vehicle_count == 0:
        return "NO_TRAFFIC"

    if speed_limit <= 0:
        return "UNKNOWN"

    speed_ratio = average_speed / speed_limit

    if speed_ratio < 0.30:
        return "HIGH"

    if speed_ratio < 0.60:
        return "MEDIUM"

    return "LOW"


def calculate_travel_time(
    road_length: float,
    speed_limit: float,
    average_speed: float,
    vehicle_count: int,
    blocked: bool = False,
) -> float:
    """
    Calculate the current estimated travel time for an edge.

    Semantics:

    EMPTY ROAD
        Use free-flow travel time based on the speed limit.
        EMPTY ROAD ≠ travel_time 0.

    FREE-FLOW / CONGESTED ROAD
        Use observed average speed.

    STOPPED ROAD
        Return infinity because the road cannot currently be
        traversed at the measured speed.

    BLOCKED ROAD
        Return infinity because the route is unavailable.

    INVALID MEASUREMENT
        Return infinity.
    """

    if road_length <= 0:
        return float("inf")

    if blocked:
        return float("inf")

    # No vehicles: passable at free-flow speed.
    if vehicle_count == 0:
        if speed_limit > 0:
            return road_length / speed_limit

        return float("inf")

    # Vehicles present but stopped.
    if average_speed <= 0:
        return float("inf")

    return road_length / average_speed


def _determine_measurement_status(
    vehicle_count: int,
    blocked: bool,
    road_length: float,
    speed_limit: float,
) -> str:
    """Classify the quality of the road measurement."""

    if blocked:
        return BLOCKED

    if road_length <= 0 or speed_limit <= 0:
        return UNKNOWN

    if vehicle_count == 0:
        return EMPTY

    return MEASURED


def build_road_state(
    traci,
    road_id: str,
    blocked: bool = False,
) -> RoadState:
    """
    Build the canonical RoadState directly from SUMO / TraCI.

    SUMO remains the source of truth for the live road measurements.
    """

    vehicle_ids = traci.edge.getLastStepVehicleIDs(road_id)
    vehicle_count = len(vehicle_ids)

    if vehicle_count > 0:
        speeds = [
            traci.vehicle.getSpeed(vid) for vid in vehicle_ids
        ]
        average_speed = sum(speeds) / vehicle_count
    else:
        average_speed = 0.0

    lane_count = traci.edge.getLaneNumber(road_id)

    if lane_count > 0:
        lane_id = f"{road_id}_0"
        road_length = traci.lane.getLength(lane_id)
        speed_limit = traci.lane.getMaxSpeed(lane_id)
    else:
        road_length = 0.0
        speed_limit = 0.0

    occupancy = traci.edge.getLastStepOccupancy(road_id)

    halting_count = traci.edge.getLastStepHaltingNumber(road_id)

    congestion = calculate_congestion(
        average_speed=average_speed,
        speed_limit=speed_limit,
        vehicle_count=vehicle_count,
    )

    travel_time = calculate_travel_time(
        road_length=road_length,
        speed_limit=speed_limit,
        average_speed=average_speed,
        vehicle_count=vehicle_count,
        blocked=blocked,
    )

    measurement_status = _determine_measurement_status(
        vehicle_count=vehicle_count,
        blocked=blocked,
        road_length=road_length,
        speed_limit=speed_limit,
    )

    return RoadState(
        road_id=road_id,
        vehicle_count=vehicle_count,
        average_speed=average_speed,
        road_length=road_length,
        speed_limit=speed_limit,
        lane_count=lane_count,
        occupancy=occupancy,
        travel_time=travel_time,
        congestion=congestion,
        blocked=blocked,
        halting_count=halting_count,
        measurement_status=measurement_status,
    )