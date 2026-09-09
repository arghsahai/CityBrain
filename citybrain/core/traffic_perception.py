from citybrain.core.road_state import RoadState


def calculate_congestion(
    average_speed: float,
    speed_limit: float,
    vehicle_count: int
) -> str:
    """
    Classify congestion based on average speed
    compared with the road speed limit.
    """

    # No vehicles means there is no traffic congestion
    if vehicle_count == 0:
        return "NO_TRAFFIC"

    if speed_limit <= 0:
        return "UNKNOWN"

    speed_ratio = average_speed / speed_limit

    if speed_ratio < 0.30:
        return "HIGH"

    elif speed_ratio < 0.60:
        return "MEDIUM"

    else:
        return "LOW"


def build_road_state(traci, road_id: str) -> RoadState:
    """
    Read road information from SUMO through TraCI
    and create a RoadState object.
    """

    # ----------------------------------------------
    # Get vehicles currently on this road
    # ----------------------------------------------

    vehicle_ids = traci.edge.getLastStepVehicleIDs(road_id)

    vehicle_count = len(vehicle_ids)


    # ----------------------------------------------
    # Calculate average speed
    # ----------------------------------------------

    if vehicle_count > 0:

        speeds = [
            traci.vehicle.getSpeed(vehicle_id)
            for vehicle_id in vehicle_ids
        ]

        average_speed = sum(speeds) / vehicle_count

    else:

        average_speed = 0.0


    # ----------------------------------------------
    # Get road information
    # ----------------------------------------------

    lane_count = traci.edge.getLaneNumber(road_id)

    # Use the first lane to obtain
    # length and speed limit

    lane_id = f"{road_id}_0"

    road_length = traci.lane.getLength(lane_id)

    speed_limit = traci.lane.getMaxSpeed(lane_id)


    # ----------------------------------------------
    # Calculate travel time
    # ----------------------------------------------

    if vehicle_count == 0:

        travel_time = 0.0

    elif average_speed > 0:

        travel_time = road_length / average_speed

    else:

        travel_time = float("inf")


    # ----------------------------------------------
    # Calculate occupancy
    # ----------------------------------------------

    occupancy = traci.edge.getLastStepOccupancy(road_id)


    # ----------------------------------------------
    # Calculate congestion
    # ----------------------------------------------

    congestion = calculate_congestion(
        average_speed,
        speed_limit,
        vehicle_count
    )


    # ----------------------------------------------
    # Create RoadState
    # ----------------------------------------------

    return RoadState(
        road_id=road_id,
        vehicle_count=vehicle_count,
        average_speed=average_speed,
        road_length=road_length,
        speed_limit=speed_limit,
        lane_count=lane_count,
        occupancy=occupancy,
        travel_time=travel_time,
        congestion=congestion
    )