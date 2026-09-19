import traci



# Emergency candidate routes.
# These are routes through the 3x3 CityBrain SUMO network.
CANDIDATE_ROUTES = {
    "R_EM_1": ["E1", "E3", "E21", "E23"],
    "R_EM_2": ["E13", "E5", "E7", "E23"],
    "R_EM_3": ["E13", "E5", "E19", "E11"],
    "R_EM_4": ["E1", "E17", "E19", "E11"],
}


def _congestion_level(mean_speed, occupancy):
    """
    Convert SUMO traffic measurements into a simple
    CityBrain congestion category.
    """

    if mean_speed <= 3.0 or occupancy >= 70.0:
        return "HIGH"

    if mean_speed <= 8.0 or occupancy >= 30.0:
        return "MEDIUM"

    return "LOW"


def _calculate_travel_time(edge_id):
    """
    Calculate travel time for a SUMO edge.

    Uses:
        travel time = edge length / current mean speed

    If the edge has no usable speed, return infinity.
    """

    lane_count = traci.edge.getLaneNumber(edge_id)

    if lane_count <= 0:
        return float("inf")

    lane_id = f"{edge_id}_0"

    edge_length = traci.lane.getLength(lane_id)
    mean_speed = traci.edge.getLastStepMeanSpeed(edge_id)

    if mean_speed <= 0:
        return float("inf")

    return edge_length / mean_speed


def build_state(city_state=None, blocked_edges=None):
    """
    Build the state dictionary expected by CityBrain's
    EmergencyPlanner.

    This converts live SUMO traffic information into
    the common state used by the AI/planning layer.
    """

    blocked_edges = set(blocked_edges or [])

    roads = {}

    for edge_id in traci.edge.getIDList():

        mean_speed = traci.edge.getLastStepMeanSpeed(edge_id)
        occupancy = traci.edge.getLastStepOccupancy(edge_id)

        travel_time = _calculate_travel_time(edge_id)

        roads[edge_id] = {
            "from": traci.edge.getFromJunction(edge_id),
            "to": traci.edge.getToJunction(edge_id),
            "travel_time": travel_time,
            "congestion": _congestion_level(
                mean_speed,
                occupancy
            ),
            "blocked": edge_id in blocked_edges,
        }

    # ---------------------------------------------------------
    # Detect ambulances currently existing in SUMO
    # ---------------------------------------------------------

    ambulances = []

    for vehicle_id in traci.vehicle.getIDList():

        vehicle_type = traci.vehicle.getTypeID(vehicle_id)

        if vehicle_type == "ambulance":

            ambulances.append(
                {
                    "id": vehicle_id,
                    "available": True,
                    "edge": traci.vehicle.getRoadID(vehicle_id),
                    "speed": traci.vehicle.getSpeed(vehicle_id),
                }
            )

    # ---------------------------------------------------------
    # Hospital
    # ---------------------------------------------------------

    hospitals = [
        {
            "id": "H1",
            "location": "J9",
            "icu_available": True,
        }
    ]

    # ---------------------------------------------------------
    # Complete CityBrain state
    # ---------------------------------------------------------

    return {
        "ambulances": ambulances,
        "hospitals": hospitals,
        "routes": CANDIDATE_ROUTES,
        "roads": roads,
        "city_state": city_state,
    }