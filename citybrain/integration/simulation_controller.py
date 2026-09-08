import copy
import traci

from citybrain.core.city_state import CityState
from citybrain.core.vehicle_state import VehicleState
from citybrain.integration.state_adapter import build_state
from citybrain.models.emergency import Emergency
from citybrain.planner.emergency_planner import EmergencyPlanner
from citybrain.planner.replanner import Replanner


SUMO_BINARY = "sumo"
SUMO_CONFIG = "simulation/scenarios/S02_accident/S02.sumocfg"

ACCIDENT_TIME = 300
ACCIDENT_EDGE = "E3"

PLAN_RETRY_INTERVAL = 5
REPLAN_INTERVAL = 30

ETA_CHANGE_THRESHOLD = 0.5


def update_city_state(city_state):
    """
    Read the current SUMO vehicle state and store it in CityState.
    """

    vehicle_ids = traci.vehicle.getIDList()
    current_vehicle_ids = set(vehicle_ids)

    for vehicle_id in vehicle_ids:

        try:

            vehicle = VehicleState(
                vehicle_id=vehicle_id,
                edge=traci.vehicle.getRoadID(vehicle_id),
                speed=traci.vehicle.getSpeed(vehicle_id),
                position=traci.vehicle.getPosition(vehicle_id),
                lane=traci.vehicle.getLaneID(vehicle_id),
                acceleration=traci.vehicle.getAcceleration(vehicle_id),
            )

            city_state.update_vehicle(vehicle)

        except traci.TraCIException:
            continue

    tracked_vehicle_ids = set(
        city_state.vehicles.keys()
    )

    for vehicle_id in tracked_vehicle_ids - current_vehicle_ids:
        city_state.remove_vehicle(vehicle_id)


def print_accident_state(current_time):
    """
    Print the current state of the accident edge.
    """

    if ACCIDENT_EDGE not in traci.edge.getIDList():
        return

    vehicle_count = traci.edge.getLastStepVehicleNumber(
        ACCIDENT_EDGE
    )

    mean_speed = traci.edge.getLastStepMeanSpeed(
        ACCIDENT_EDGE
    )

    occupancy = traci.edge.getLastStepOccupancy(
        ACCIDENT_EDGE
    )

    print(
        f"[{current_time:.0f}s] "
        f"{ACCIDENT_EDGE}: "
        f"vehicles={vehicle_count}, "
        f"speed={mean_speed:.2f}, "
        f"occupancy={occupancy:.2f}"
    )


def print_citybrain_state(planner_state):
    """
    Print the state that CityBrain gives to the planner.
    """

    print()
    print("---------- CITYBRAIN STATE ----------")

    print(
        f"Ambulances: "
        f"{planner_state.get('ambulances', [])}"
    )

    print(
        f"Hospitals: "
        f"{planner_state.get('hospitals', [])}"
    )

    blocked_edges = [
        edge
        for edge, data in planner_state.get(
            "roads", {}
        ).items()
        if data.get("blocked")
    ]

    print(
        f"Blocked edges: {blocked_edges}"
    )

    print("-------------------------------------")
    print()


def print_plan(plan_name, emergency, plan):
    """
    Print an emergency plan.
    """

    print()
    print("==============================================")
    print(f"       {plan_name}")
    print("==============================================")

    print(
        f"Emergency : {emergency.emergency_id}"
    )

    print(
        f"Ambulance : {plan.ambulance_id}"
    )

    print(
        f"Hospital  : {plan.hospital_id}"
    )

    print(
        f"Route     : {' -> '.join(plan.route)}"
    )

    print(
        f"ETA       : {plan.eta:.2f} seconds"
    )

    print(
        f"Signal    : {plan.signal_priority}"
    )

    print("==============================================")
    print()


def get_ambulance_edge(ambulance_id):
    """
    Return the ambulance's current SUMO edge.
    """

    if ambulance_id not in traci.vehicle.getIDList():
        return None

    try:

        return traci.vehicle.getRoadID(
            ambulance_id
        )

    except traci.TraCIException:

        return None


def make_executable_route(ambulance_id, planned_route):
    """
    Convert a CityBrain planned route into a route that
    can actually be assigned from the ambulance's
    current SUMO position.

    Example:

        Planned:
        E13 -> E5 -> E19 -> E11

        Ambulance currently on:
        E5

        Executable:
        E5 -> E19 -> E11
    """

    current_edge = get_ambulance_edge(
        ambulance_id
    )

    if current_edge is None:

        print(
            f"[CityBrain] Could not determine "
            f"current edge of {ambulance_id}."
        )

        return None

    print(
        f"[CityBrain] Ambulance current edge: "
        f"{current_edge}"
    )

    planned_route = list(planned_route)

    if current_edge in planned_route:

        current_index = planned_route.index(
            current_edge
        )

        executable_route = planned_route[
            current_index:
        ]

        print(
            "[CityBrain] Executable route: "
            f"{' -> '.join(executable_route)}"
        )

        return executable_route

    print(
        "[CityBrain] Current ambulance edge "
        "is not present in the planned route."
    )

    return None


def apply_ambulance_route(plan):
    """
    Apply the selected CityBrain route to the ambulance.

    The route is adjusted according to the ambulance's
    current SUMO edge before being assigned.
    """

    ambulance_id = plan.ambulance_id

    if ambulance_id not in traci.vehicle.getIDList():

        print(
            f"[CityBrain] Ambulance {ambulance_id} "
            f"is no longer in SUMO."
        )

        return False

    executable_route = make_executable_route(
        ambulance_id,
        plan.route,
    )

    if not executable_route:

        print(
            "[CityBrain] Could not construct "
            "an executable route."
        )

        return False

    try:

        traci.vehicle.setRoute(
            ambulance_id,
            executable_route,
        )

        print()
        print(
            f"[CityBrain] Route assigned to "
            f"{ambulance_id}:"
        )

        print(
            f"    {' -> '.join(executable_route)}"
        )

        print()

        return True

    except traci.TraCIException as error:

        print(
            f"[CityBrain] Could not assign "
            f"ambulance route: {error}"
        )

        return False


def route_changed(old_route, new_route):
    """
    Check whether the emergency route changed.
    """

    return list(old_route) != list(new_route)


def eta_changed(old_eta, new_eta):
    """
    Check whether the estimated travel time changed
    meaningfully.
    """

    return (
        abs(old_eta - new_eta)
        >= ETA_CHANGE_THRESHOLD
    )


def run_simulation():

    print()
    print("==============================================")
    print("       CITYBRAIN EMERGENCY SIMULATION")
    print("==============================================")
    print()

    city_state = CityState()

    planner = EmergencyPlanner()

    replanner = Replanner()

    emergency = Emergency(
        emergency_id="EM001",
        location="J3",
        severity="HIGH",
        emergency_type="ROAD_ACCIDENT",
    )

    initial_plan = None

    accident_detected = False

    last_plan_attempt = -PLAN_RETRY_INTERVAL

    last_replan_time = -REPLAN_INTERVAL

    try:

        traci.start(
            [
                SUMO_BINARY,
                "-c",
                SUMO_CONFIG,
                "--step-length",
                "1",
            ]
        )

        while (
            traci.simulation.getMinExpectedNumber()
            > 0
        ):

            traci.simulationStep()

            current_time = (
                traci.simulation.getTime()
            )

            update_city_state(
                city_state
            )

            if current_time % 30 == 0:

                print(
                    f"[{current_time:.0f}s] "
                    f"CityState vehicles = "
                    f"{city_state.vehicle_count()}"
                )

            # ==================================================
            # ACCIDENT DETECTION
            # ==================================================

            if (
                current_time >= ACCIDENT_TIME
                and not accident_detected
            ):

                accident_detected = True

                print()
                print(
                    "****************************************"
                )
                print(
                    "       ACCIDENT DETECTED"
                )
                print(
                    "****************************************"
                )

                print(
                    f"Time : "
                    f"{current_time:.0f}s"
                )

                print(
                    f"Location : "
                    f"{ACCIDENT_EDGE}"
                )

                print_accident_state(
                    current_time
                )

                print()

                print(
                    "CityBrain is waiting for an "
                    "available ambulance..."
                )

                print()

            # ==================================================
            # INITIAL PLAN P0
            # ==================================================

            if (
                accident_detected
                and initial_plan is None
                and (
                    current_time
                    - last_plan_attempt
                    >= PLAN_RETRY_INTERVAL
                )
            ):

                last_plan_attempt = current_time

                blocked_edges = {
                    ACCIDENT_EDGE
                }

                planner_state = build_state(
                    city_state,
                    blocked_edges=blocked_edges,
                )

                ambulances = (
                    planner_state.get(
                        "ambulances",
                        [],
                    )
                )

                if not ambulances:

                    print(
                        f"[CityBrain] "
                        f"No ambulance available "
                        f"at {current_time:.0f}s. "
                        f"Retrying P0 later."
                    )

                else:

                    print_citybrain_state(
                        planner_state
                    )

                    print(
                        "CityBrain is creating "
                        "initial plan P0..."
                    )

                    initial_plan = (
                        planner.create_plan(
                            emergency,
                            planner_state,
                        )
                    )

                    if initial_plan is not None:

                        print_plan(
                            "INITIAL EMERGENCY PLAN P0",
                            emergency,
                            initial_plan,
                        )

                        route_applied = (
                            apply_ambulance_route(
                                initial_plan
                            )
                        )

                        if route_applied:

                            last_replan_time = (
                                current_time
                            )

                            print(
                                "[CityBrain] "
                                "P0 successfully "
                                "dispatched."
                            )

                        else:

                            print(
                                "[CityBrain] "
                                "P0 was created but "
                                "the route could not "
                                "be assigned."
                            )

                    else:

                        print(
                            "[CityBrain] "
                            "P0 could not be "
                            "created. "
                            "CityBrain will retry "
                            "later."
                        )

            # ==================================================
            # DYNAMIC REPLANNING
            # ==================================================

            if (
                accident_detected
                and initial_plan is not None
                and (
                    current_time
                    - last_replan_time
                    >= REPLAN_INTERVAL
                )
            ):

                blocked_edges = {
                    ACCIDENT_EDGE
                }

                planner_state = build_state(
                    city_state,
                    blocked_edges=blocked_edges,
                )

                print()
                print(
                    f"[CityBrain] Re-evaluating "
                    f"emergency plan at "
                    f"{current_time:.0f}s..."
                )

                # Preserve the old plan.
                previous_plan = (
                    copy.deepcopy(
                        initial_plan
                    )
                )

                # Give the replanner a copy so that
                # the current plan is not overwritten.
                candidate_plan = (
                    copy.deepcopy(
                        initial_plan
                    )
                )

                updated_plan = (
                    replanner.replan(
                        candidate_plan,
                        planner_state,
                    )
                )

                if updated_plan is not None:

                    print_plan(
                        "UPDATED EMERGENCY PLAN",
                        emergency,
                        updated_plan,
                    )

                    route_was_changed = (
                        route_changed(
                            previous_plan.route,
                            updated_plan.route,
                        )
                    )

                    eta_was_changed = (
                        eta_changed(
                            previous_plan.eta,
                            updated_plan.eta,
                        )
                    )

                    # ==========================================
                    # ROUTE CHANGED
                    # ==========================================

                    if route_was_changed:

                        print()
                        print(
                            "[CityBrain] "
                            "ROUTE CHANGE DETECTED"
                        )

                        print(
                            "Old route : "
                            f"{' -> '.join(previous_plan.route)}"
                        )

                        print(
                            "New route : "
                            f"{' -> '.join(updated_plan.route)}"
                        )

                        print()

                        route_applied = (
                            apply_ambulance_route(
                                updated_plan
                            )
                        )

                        if route_applied:

                            initial_plan = (
                                updated_plan
                            )

                            print(
                                "[CityBrain] "
                                "New route successfully "
                                "applied."
                            )

                        else:

                            print(
                                "[CityBrain] "
                                "New route could not "
                                "be applied."
                            )

                    # ==========================================
                    # ETA CHANGED
                    # ==========================================

                    elif eta_was_changed:

                        print()
                        print(
                            "[CityBrain] "
                            "Route remains the same, "
                            "but ETA changed."
                        )

                        print(
                            f"Old ETA : "
                            f"{previous_plan.eta:.2f}s"
                        )

                        print(
                            f"New ETA : "
                            f"{updated_plan.eta:.2f}s"
                        )

                        initial_plan = (
                            updated_plan
                        )

                    # ==========================================
                    # NOTHING CHANGED
                    # ==========================================

                    else:

                        print()
                        print(
                            "[CityBrain] "
                            "Current emergency plan "
                            "remains unchanged."
                        )

                else:

                    print()
                    print(
                        "[CityBrain] "
                        "No valid updated "
                        "plan available."
                    )

                last_replan_time = (
                    current_time
                )

            # ==================================================
            # ACCIDENT MONITORING
            # ==================================================

            if (
                accident_detected
                and current_time % 30 == 0
            ):

                print_accident_state(
                    current_time
                )

    except KeyboardInterrupt:

        print()
        print(
            "[CityBrain] Simulation "
            "interrupted by user."
        )

    except traci.TraCIException as error:

        print()
        print(
            f"[CityBrain] TraCI error: "
            f"{error}"
        )

    finally:

        try:

            traci.close()

        except (
            traci.TraCIException,
            KeyError,
            ConnectionError,
        ):

            pass

        print()
        print(
            "CityBrain simulation finished."
        )


if __name__ == "__main__":
    run_simulation()