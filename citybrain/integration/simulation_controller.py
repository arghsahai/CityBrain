import copy
import csv
import os

import traci

from experiments.outcomes import classify_step

from citybrain.core.city_state import CityState
from citybrain.core.vehicle_state import VehicleState
from citybrain.integration.state_adapter import build_state
from citybrain.models.emergency import Emergency
from citybrain.planner.emergency_planner import EmergencyPlanner
from citybrain.planner.replanner import Replanner


# ================================================================
# SUMO CONFIGURATION
# ================================================================

SUMO_BINARY = "sumo"

SUMO_CONFIG = (
    "simulation/scenarios/S05_dynamic_blockage/S05.sumocfg"
)


# ================================================================
# CITYBRAIN TIMING
# ================================================================

ACCIDENT_TIME = 300

DYNAMIC_BLOCKAGE_TIME = 307

PLAN_RETRY_INTERVAL = 1

REPLAN_INTERVAL = 10

ETA_CHANGE_THRESHOLD = 0.5


# ================================================================
# ROAD CONDITIONS
# ================================================================

ACCIDENT_EDGE = "E3"

DYNAMIC_BLOCKAGE_EDGE = "E7"


# ================================================================
# EXPERIMENT LOGGING
# ================================================================

RESULTS_DIR = "experiments/results"

RESULTS_FILE = os.path.join(
    RESULTS_DIR,
    "s05_dynamic_replanning.csv"
)

EXPERIMENT_FIELDS = [
    "scenario",
    "emergency_id",
    "accident_time",
    "blockage_time",
    "initial_route",
    "replanned_route",
    "initial_eta",
    "replanned_eta",
    "replanning_time",
    "replanning_latency",
    "ambulance_completion_time",
    "number_of_replans",
    "route_changed",
    "completed",
    "completion_status",
    "teleported",
]


def initialize_experiment_log():
    """
    Create the experiment results directory and CSV file.
    A new file is created for every simulation run.
    """

    os.makedirs(
        RESULTS_DIR,
        exist_ok=True
    )

    with open(
        RESULTS_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=EXPERIMENT_FIELDS,
        )

        writer.writeheader()


def write_experiment_result(result):
    """
    Append one completed experiment result to the CSV file.
    """

    os.makedirs(
        RESULTS_DIR,
        exist_ok=True
    )

    file_exists = os.path.exists(
        RESULTS_FILE
    )

    with open(
        RESULTS_FILE,
        "a",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=EXPERIMENT_FIELDS,
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(result)


def route_to_string(route):
    """
    Convert a route list into a readable string.
    """

    if not route:
        return ""

    return " -> ".join(route)


# ================================================================
# CITY STATE
# ================================================================

def update_city_state(city_state):

    vehicle_ids = traci.vehicle.getIDList()

    current_vehicle_ids = set(
        vehicle_ids
    )

    for vehicle_id in vehicle_ids:

        try:

            vehicle = VehicleState(
                vehicle_id=vehicle_id,
                edge=traci.vehicle.getRoadID(
                    vehicle_id
                ),
                speed=traci.vehicle.getSpeed(
                    vehicle_id
                ),
                position=traci.vehicle.getPosition(
                    vehicle_id
                ),
                lane=traci.vehicle.getLaneID(
                    vehicle_id
                ),
                acceleration=traci.vehicle.getAcceleration(
                    vehicle_id
                ),
            )

            city_state.update_vehicle(
                vehicle
            )

        except traci.TraCIException:

            continue

    tracked_vehicle_ids = set(
        city_state.vehicles.keys()
    )

    for vehicle_id in (
        tracked_vehicle_ids
        - current_vehicle_ids
    ):

        city_state.remove_vehicle(
            vehicle_id
        )


# ================================================================
# ROAD STATE
# ================================================================

def print_road_state(
    current_time,
    edge_id,
):

    if edge_id not in (
        traci.edge.getIDList()
    ):

        return

    vehicle_count = (
        traci.edge.getLastStepVehicleNumber(
            edge_id
        )
    )

    mean_speed = (
        traci.edge.getLastStepMeanSpeed(
            edge_id
        )
    )

    occupancy = (
        traci.edge.getLastStepOccupancy(
            edge_id
        )
    )

    print(
        f"[{current_time:.0f}s] "
        f"{edge_id}: "
        f"vehicles={vehicle_count}, "
        f"speed={mean_speed:.2f}, "
        f"occupancy={occupancy:.2f}"
    )


# ================================================================
# CITYBRAIN STATE
# ================================================================

def print_citybrain_state(
    planner_state
):

    print()
    print(
        "---------- CITYBRAIN STATE ----------"
    )

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
            "roads",
            {}
        ).items()
        if data.get("blocked")
    ]

    print(
        f"Blocked edges: "
        f"{blocked_edges}"
    )

    print(
        "-------------------------------------"
    )

    print()


# ================================================================
# PLAN DISPLAY
# ================================================================

def print_plan(
    plan_name,
    emergency,
    plan,
):

    print()
    print(
        "=============================================="
    )

    print(
        f"       {plan_name}"
    )

    print(
        "=============================================="
    )

    print(
        f"Emergency : "
        f"{emergency.emergency_id}"
    )

    print(
        f"Ambulance : "
        f"{plan.ambulance_id}"
    )

    print(
        f"Hospital  : "
        f"{plan.hospital_id}"
    )

    print(
        f"Route     : "
        f"{route_to_string(plan.route)}"
    )

    print(
        f"ETA       : "
        f"{plan.eta:.2f} seconds"
    )

    print(
        f"Signal    : "
        f"{plan.signal_priority}"
    )

    print(
        "=============================================="
    )

    print()


# ================================================================
# AMBULANCE POSITION
# ================================================================

def get_ambulance_edge(
    ambulance_id
):

    if ambulance_id not in (
        traci.vehicle.getIDList()
    ):

        return None

    try:

        return traci.vehicle.getRoadID(
            ambulance_id
        )

    except traci.TraCIException:

        return None


# ================================================================
# EXECUTABLE ROUTE
# ================================================================

def make_executable_route(
    ambulance_id,
    planned_route,
):

    current_edge = get_ambulance_edge(
        ambulance_id
    )

    if current_edge is None:

        print(
            "[CityBrain] Could not determine "
            f"current edge of {ambulance_id}."
        )

        return None

    print(
        "[CityBrain] Ambulance current edge: "
        f"{current_edge}"
    )

    planned_route = list(
        planned_route
    )

    if current_edge in planned_route:

        current_index = (
            planned_route.index(
                current_edge
            )
        )

        executable_route = (
            planned_route[current_index:]
        )

        print(
            "[CityBrain] Executable route: "
            f"{route_to_string(executable_route)}"
        )

        return executable_route

    print(
        "[CityBrain] Current ambulance edge "
        "is not present in the planned route."
    )

    return None


# ================================================================
# APPLY AMBULANCE ROUTE
# ================================================================

def apply_ambulance_route(
    plan
):

    ambulance_id = (
        plan.ambulance_id
    )

    if ambulance_id not in (
        traci.vehicle.getIDList()
    ):

        print(
            "[CityBrain] Ambulance "
            f"{ambulance_id} is no longer in SUMO."
        )

        return False

    executable_route = (
        make_executable_route(
            ambulance_id,
            plan.route,
        )
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
            "[CityBrain] Route assigned to "
            f"{ambulance_id}:"
        )

        print(
            f"    {route_to_string(executable_route)}"
        )

        print()

        return True

    except traci.TraCIException as error:

        print(
            "[CityBrain] Could not assign "
            f"ambulance route: {error}"
        )

        return False


# ================================================================
# PLAN COMPARISON
# ================================================================

def route_changed(
    old_route,
    new_route,
):

    return (
        list(old_route)
        != list(new_route)
    )


def eta_changed(
    old_eta,
    new_eta,
):

    return (
        abs(
            old_eta
            - new_eta
        )
        >= ETA_CHANGE_THRESHOLD
    )


# ================================================================
# EXPERIMENT RESULT
# ================================================================

def create_experiment_result(
    emergency,
    initial_route,
    replanned_route,
    initial_eta,
    replanned_eta,
    replanning_time,
    replanning_latency,
    ambulance_completion_time,
    number_of_replans,
    route_was_changed,
    completed,
    completion_status=None,
):

    return {
        "scenario": "S05_dynamic_blockage",

        "emergency_id":
            emergency.emergency_id,

        "accident_time":
            ACCIDENT_TIME,

        "blockage_time":
            DYNAMIC_BLOCKAGE_TIME,

        "initial_route":
            route_to_string(
                initial_route
            ),

        "replanned_route":
            route_to_string(
                replanned_route
            ),

        "initial_eta":
            (
                ""
                if initial_eta is None
                else f"{initial_eta:.4f}"
            ),

        "replanned_eta":
            (
                ""
                if replanned_eta is None
                else f"{replanned_eta:.4f}"
            ),

        "replanning_time":
            (
                ""
                if replanning_time is None
                else f"{replanning_time:.0f}"
            ),

        "replanning_latency":
            (
                ""
                if replanning_latency is None
                else f"{replanning_latency:.0f}"
            ),

        "ambulance_completion_time":
            (
                ""
                if ambulance_completion_time is None
                else f"{ambulance_completion_time:.0f}"
            ),

        "number_of_replans":
            number_of_replans,

        "route_changed":
            route_was_changed,

        "completed":
            completed,
        "completion_status": completion_status or ("SUCCESS" if completed else "TIMEOUT"),
        "teleported": completion_status == "TELEPORTED",
    }


# ================================================================
# MAIN SIMULATION
# ================================================================

def run_simulation():

    print()
    print(
        "=============================================="
    )

    print(
        "       CITYBRAIN DYNAMIC EMERGENCY"
    )

    print(
        "       RESPONSE SIMULATION"
    )

    print(
        "=============================================="
    )

    print()

    # ============================================================
    # INITIALIZE EXPERIMENT LOG
    # ============================================================

    initialize_experiment_log()

    print(
        "[Experiment] Results will be saved to:"
    )

    print(
        f"    {RESULTS_FILE}"
    )

    print()

    # ============================================================
    # CITYBRAIN OBJECTS
    # ============================================================

    city_state = CityState()

    planner = EmergencyPlanner()

    replanner = Replanner()

    emergency = Emergency(
        emergency_id="EM001",
        location="J3",
        severity="HIGH",
        emergency_type="ROAD_ACCIDENT",
    )

    current_plan = None

    # ============================================================
    # EXPERIMENT VARIABLES
    # ============================================================

    accident_detected = False

    dynamic_blockage_detected = False

    emergency_finished = False

    result_written = False

    initial_route = []

    replanned_route = []

    initial_eta = None

    replanned_eta = None

    replanning_time = None

    replanning_latency = None

    ambulance_completion_time = None

    number_of_replans = 0

    route_was_changed = False

    last_plan_attempt = (
        -PLAN_RETRY_INTERVAL
    )

    last_replan_time = (
        -REPLAN_INTERVAL
    )

    try:

        # ========================================================
        # START SUMO
        # ========================================================

        traci.start(
            [
                SUMO_BINARY,
                "-c",
                SUMO_CONFIG,
                "--step-length",
                "1",
            ]
        )

        print(
            "[CityBrain] SUMO simulation started."
        )

        # ========================================================
        # SIMULATION LOOP
        # ========================================================

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

            # ====================================================
            # CITY STATE MONITORING
            # ====================================================

            if current_time % 30 == 0:

                print(
                    f"[{current_time:.0f}s] "
                    f"CityState vehicles = "
                    f"{city_state.vehicle_count()}"
                )

            # ====================================================
            # ACCIDENT DETECTION
            # ====================================================

            if (
                current_time
                >= ACCIDENT_TIME
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

                print_road_state(
                    current_time,
                    ACCIDENT_EDGE,
                )

                print()

                print(
                    "CityBrain is creating "
                    "the initial emergency plan..."
                )

                print()

            # ====================================================
            # INITIAL PLAN P0
            # ====================================================

            if (
                accident_detected
                and current_plan is None
                and not emergency_finished
                and (
                    current_time
                    - last_plan_attempt
                    >= PLAN_RETRY_INTERVAL
                )
            ):

                last_plan_attempt = (
                    current_time
                )

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
                        []
                    )
                )

                if not ambulances:

                    print(
                        "[CityBrain] "
                        f"No ambulance available "
                        f"at {current_time:.0f}s."
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

                            current_plan = (
                                initial_plan
                            )

                            initial_route = list(
                                initial_plan.route
                            )

                            initial_eta = (
                                initial_plan.eta
                            )

                            last_replan_time = (
                                current_time
                            )

                            print(
                                "[CityBrain] "
                                "P0 successfully dispatched."
                            )

                        else:

                            print(
                                "[CityBrain] "
                                "P0 was created, "
                                "but could not be "
                                "physically dispatched."
                            )

            # ====================================================
            # DYNAMIC BLOCKAGE
            # ====================================================

            force_replan = False

            if (
                accident_detected
                and current_time
                >= DYNAMIC_BLOCKAGE_TIME
                and not dynamic_blockage_detected
            ):

                dynamic_blockage_detected = True

                force_replan = True

                print()
                print(
                    "################################################"
                )

                print(
                    "       DYNAMIC ROAD BLOCKAGE DETECTED"
                )

                print(
                    "################################################"
                )

                print(
                    f"Time : "
                    f"{current_time:.0f}s"
                )

                print(
                    f"Blocked road : "
                    f"{DYNAMIC_BLOCKAGE_EDGE}"
                )

                print_road_state(
                    current_time,
                    DYNAMIC_BLOCKAGE_EDGE,
                )

                print()

                print(
                    "[CityBrain] "
                    "The current emergency plan "
                    "may now be invalid."
                )

                print(
                    "[CityBrain] "
                    "FORCING IMMEDIATE REPLANNING."
                )

                print()

            # ====================================================
            # CHECK AMBULANCE
            # ====================================================

            ambulance_present = False

            if current_plan is not None:

                ambulance_present = (
                    current_plan.ambulance_id
                    in traci.vehicle.getIDList()
                )

                outcome = classify_step(
                    current_plan.ambulance_id, traci.vehicle.getIDList(),
                    traci.simulation.getArrivedIDList(),
                    traci.simulation.getStartingTeleportIDList(),
                )

                if outcome is not None:

                    if not emergency_finished:

                        ambulance_completion_time = (
                            current_time if outcome == "SUCCESS" else None
                        )

                        print()
                        print(
                            "[CityBrain] Ambulance "
                            f"{current_plan.ambulance_id} "
                            f"outcome: {outcome}; "
                            "the SUMO simulation."
                        )

                        print(
                            "[CityBrain] "
                            "Emergency response "
                            "execution finished."
                        )

                        print()

                        emergency_finished = True

                        # ========================================
                        # WRITE FINAL EXPERIMENT RESULT
                        # ========================================

                        result = (
                            create_experiment_result(
                                emergency,
                                initial_route,
                                replanned_route,
                                initial_eta,
                                replanned_eta,
                                replanning_time,
                                replanning_latency,
                                ambulance_completion_time,
                                number_of_replans,
                                route_was_changed,
                                outcome == "SUCCESS",
                                outcome,
                            )
                        )

                        write_experiment_result(
                            result
                        )

                        result_written = True

                        print(
                            "[Experiment] "
                            "S05 result saved."
                        )

            # ====================================================
            # DYNAMIC REPLANNING
            # ====================================================

            if (
                accident_detected
                and current_plan is not None
                and ambulance_present
                and not emergency_finished
                and (
                    force_replan
                    or (
                        current_time
                        - last_replan_time
                        >= REPLAN_INTERVAL
                    )
                )
            ):

                last_replan_time = (
                    current_time
                )

                blocked_edges = {
                    ACCIDENT_EDGE
                }

                if dynamic_blockage_detected:

                    blocked_edges.add(
                        DYNAMIC_BLOCKAGE_EDGE
                    )

                planner_state = build_state(
                    city_state,
                    blocked_edges=blocked_edges,
                )

                print()
                print(
                    "[CityBrain] "
                    f"Re-evaluating emergency plan "
                    f"at {current_time:.0f}s..."
                )

                print_citybrain_state(
                    planner_state
                )

                previous_plan = (
                    copy.deepcopy(
                        current_plan
                    )
                )

                candidate_plan = (
                    copy.deepcopy(
                        current_plan
                    )
                )

                updated_plan = (
                    replanner.replan(
                        candidate_plan,
                        planner_state,
                    )
                )

                if updated_plan is None:

                    print(
                        "[CityBrain] "
                        "No valid updated plan available."
                    )

                    continue

                print_plan(
                    "UPDATED EMERGENCY PLAN",
                    emergency,
                    updated_plan,
                )

                route_was_changed_now = (
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

                # =================================================
                # ROUTE CHANGE
                # =================================================

                if route_was_changed_now:

                    print()
                    print(
                        "[CityBrain] "
                        "ROUTE CHANGE DETECTED"
                    )

                    print(
                        "Old route : "
                        f"{route_to_string(previous_plan.route)}"
                    )

                    print(
                        "New route : "
                        f"{route_to_string(updated_plan.route)}"
                    )

                    print()

                    route_applied = (
                        apply_ambulance_route(
                            updated_plan
                        )
                    )

                    if route_applied:

                        current_plan = (
                            updated_plan
                        )

                        number_of_replans += 1

                        if not route_was_changed:

                            replanned_route = list(
                                updated_plan.route
                            )

                            replanned_eta = (
                                updated_plan.eta
                            )

                            replanning_time = (
                                current_time
                            )

                            replanning_latency = (
                                current_time
                                - DYNAMIC_BLOCKAGE_TIME
                            )

                        route_was_changed = True

                        print(
                            "[CityBrain] "
                            "NEW ROUTE SUCCESSFULLY "
                            "APPLIED."
                        )

                        print(
                            "[Experiment] "
                            f"Replan count = "
                            f"{number_of_replans}"
                        )

                    else:

                        print(
                            "[CityBrain] "
                            "New route could not "
                            "be applied."
                        )

                # =================================================
                # ETA CHANGE
                # =================================================

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

                    current_plan = (
                        updated_plan
                    )

                # =================================================
                # NO CHANGE
                # =================================================

                else:

                    print()

                    print(
                        "[CityBrain] "
                        "Current emergency plan "
                        "remains unchanged."
                    )

        # ========================================================
        # SIMULATION ENDED
        # ========================================================

        if (
            not result_written
            and current_plan is not None
        ):

            result = (
                create_experiment_result(
                    emergency,
                    initial_route,
                    replanned_route,
                    initial_eta,
                    replanned_eta,
                    replanning_time,
                    replanning_latency,
                    ambulance_completion_time,
                    number_of_replans,
                    route_was_changed,
                    emergency_finished,
                )
            )

            write_experiment_result(
                result
            )

            result_written = True

            print(
                "[Experiment] "
                "Final S05 result saved."
            )

    except KeyboardInterrupt:

        print()

        print(
            "[CityBrain] "
            "Simulation interrupted by user."
        )

    except traci.TraCIException as error:

        print()

        print(
            "[CityBrain] TraCI error: "
            f"{error}"
        )

    finally:

        try:

            traci.close()

        except Exception:

            pass

        print()

        print(
            "CityBrain simulation finished."
        )

        print(
            f"[Experiment] Results file: "
            f"{RESULTS_FILE}"
        )


# ================================================================
# ENTRY POINT
# ================================================================

if __name__ == "__main__":

    run_simulation()