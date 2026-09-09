import csv
import os

import traci

from citybrain.core.city_state import CityState
from citybrain.core.vehicle_state import VehicleState
from citybrain.integration.state_adapter import build_state
from citybrain.models.emergency import Emergency
from citybrain.planner.emergency_planner import EmergencyPlanner


SUMO_BINARY = "sumo"

SUMO_CONFIG = (
    "simulation/scenarios/S05_dynamic_blockage/S05.sumocfg"
)

ACCIDENT_TIME = 300
DYNAMIC_BLOCKAGE_TIME = 307
PLAN_RETRY_INTERVAL = 1

ACCIDENT_EDGE = "E3"
DYNAMIC_BLOCKAGE_EDGE = "E7"

RESULTS_DIR = "experiments/results"

RESULTS_FILE = os.path.join(
    RESULTS_DIR,
    "s05_static_baseline.csv"
)

EXPERIMENT_FIELDS = [
    "scenario",
    "emergency_id",
    "accident_time",
    "blockage_time",
    "initial_route",
    "initial_eta",
    "ambulance_completion_time",
    "actual_response_time",
    "number_of_replans",
    "route_changed",
    "completed",
]


def initialize_experiment_log():

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

    if not route:
        return ""

    return " -> ".join(route)


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


def print_road_state(
    current_time,
    edge_id,
):

    if edge_id not in traci.edge.getIDList():

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


def print_citybrain_state(planner_state):

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


def get_ambulance_edge(ambulance_id):

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


def make_executable_route(
    ambulance_id,
    planned_route,
):

    current_edge = get_ambulance_edge(
        ambulance_id
    )

    if current_edge is None:

        print(
            "[Static Baseline] Could not determine "
            f"current edge of {ambulance_id}."
        )

        return None

    print(
        "[Static Baseline] Ambulance current edge: "
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
            "[Static Baseline] Executable route: "
            f"{route_to_string(executable_route)}"
        )

        return executable_route

    print(
        "[Static Baseline] Current ambulance edge "
        "is not present in the planned route."
    )

    return None


def apply_ambulance_route(plan):

    ambulance_id = (
        plan.ambulance_id
    )

    if ambulance_id not in (
        traci.vehicle.getIDList()
    ):

        print(
            "[Static Baseline] Ambulance "
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

        return False

    try:

        traci.vehicle.setRoute(
            ambulance_id,
            executable_route,
        )

        print()

        print(
            "[Static Baseline] Route assigned to "
            f"{ambulance_id}:"
        )

        print(
            f"    {route_to_string(executable_route)}"
        )

        print()

        return True

    except traci.TraCIException as error:

        print(
            "[Static Baseline] Could not assign "
            f"ambulance route: {error}"
        )

        return False


def create_experiment_result(
    emergency,
    initial_route,
    initial_eta,
    ambulance_completion_time,
    completed,
):

    actual_response_time = None

    if ambulance_completion_time is not None:

        actual_response_time = (
            ambulance_completion_time
            - ACCIDENT_TIME
        )

    return {
        "scenario":
            "S05_static_baseline",

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

        "initial_eta":
            (
                ""
                if initial_eta is None
                else f"{initial_eta:.4f}"
            ),

        "ambulance_completion_time":
            (
                ""
                if ambulance_completion_time is None
                else f"{ambulance_completion_time:.0f}"
            ),

        "actual_response_time":
            (
                ""
                if actual_response_time is None
                else f"{actual_response_time:.0f}"
            ),

        "number_of_replans":
            0,

        "route_changed":
            False,

        "completed":
            completed,
    }


def run_simulation():

    print()
    print(
        "=============================================="
    )

    print(
        "       CITYBRAIN STATIC BASELINE"
    )

    print(
        "       EMERGENCY RESPONSE SIMULATION"
    )

    print(
        "=============================================="
    )

    print()

    initialize_experiment_log()

    print(
        "[Experiment] Results will be saved to:"
    )

    print(
        f"    {RESULTS_FILE}"
    )

    print()

    city_state = CityState()

    planner = EmergencyPlanner()

    emergency = Emergency(
        emergency_id="EM001",
        location="J3",
        severity="HIGH",
        emergency_type="ROAD_ACCIDENT",
    )

    current_plan = None

    accident_detected = False

    dynamic_blockage_detected = False

    emergency_finished = False

    result_written = False

    initial_route = []

    initial_eta = None

    ambulance_completion_time = None

    last_plan_attempt = (
        -PLAN_RETRY_INTERVAL
    )

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

        print(
            "[CityBrain] SUMO simulation started."
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

            # ----------------------------------------------------
            # ACCIDENT
            # ----------------------------------------------------

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
                    f"Time : {current_time:.0f}s"
                )

                print(
                    f"Location : {ACCIDENT_EDGE}"
                )

                print_road_state(
                    current_time,
                    ACCIDENT_EDGE,
                )

                print()

                print(
                    "[Static Baseline] Creating "
                    "initial emergency plan P0..."
                )

            # ----------------------------------------------------
            # INITIAL PLAN
            # ----------------------------------------------------

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

                planner_state = build_state(
                    city_state,
                    blocked_edges={
                        ACCIDENT_EDGE
                    },
                )

                ambulances = (
                    planner_state.get(
                        "ambulances",
                        []
                    )
                )

                if not ambulances:

                    print(
                        "[Static Baseline] "
                        f"No ambulance available "
                        f"at {current_time:.0f}s."
                    )

                else:

                    print_citybrain_state(
                        planner_state
                    )

                    initial_plan = (
                        planner.create_plan(
                            emergency,
                            planner_state,
                        )
                    )

                    if initial_plan is not None:

                        print_plan(
                            "STATIC BASELINE PLAN P0",
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

                            print(
                                "[Static Baseline] "
                                "P0 successfully dispatched."
                            )

            # ----------------------------------------------------
            # BLOCKAGE
            # ----------------------------------------------------

            if (
                accident_detected
                and current_time >= DYNAMIC_BLOCKAGE_TIME
                and not dynamic_blockage_detected
            ):

                dynamic_blockage_detected = True

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
                    f"Time : {current_time:.0f}s"
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
                    "[Static Baseline] "
                    "NO REPLANNING WILL BE PERFORMED."
                )

                print(
                    "[Static Baseline] "
                    "Ambulance continues with original P0 route."
                )

                print()

            # ----------------------------------------------------
            # CHECK AMBULANCE
            # ----------------------------------------------------

            if current_plan is not None:

                ambulance_id = (
                    current_plan.ambulance_id
                )

                ambulance_present = (
                    ambulance_id
                    in traci.vehicle.getIDList()
                )

                if not ambulance_present:

                    if not emergency_finished:

                        ambulance_completion_time = (
                            current_time
                        )

                        print()
                        print(
                            "[Static Baseline] Ambulance "
                            f"{ambulance_id} has completed "
                            "or left the SUMO simulation."
                        )

                        print(
                            "[Static Baseline] "
                            "Emergency response execution finished."
                        )

                        emergency_finished = True

                        result = (
                            create_experiment_result(
                                emergency,
                                initial_route,
                                initial_eta,
                                ambulance_completion_time,
                                True,
                            )
                        )

                        write_experiment_result(
                            result
                        )

                        result_written = True

                        print(
                            "[Experiment] "
                            "S05 static baseline result saved."
                        )

        # --------------------------------------------------------
        # FINAL RESULT
        # --------------------------------------------------------

        if (
            not result_written
            and current_plan is not None
        ):

            result = (
                create_experiment_result(
                    emergency,
                    initial_route,
                    initial_eta,
                    ambulance_completion_time,
                    emergency_finished,
                )
            )

            write_experiment_result(
                result
            )

            result_written = True

            print(
                "[Experiment] "
                "Final S05 static baseline result saved."
            )

    except KeyboardInterrupt:

        print()

        print(
            "[Static Baseline] "
            "Simulation interrupted by user."
        )

    except traci.TraCIException as error:

        print()

        print(
            "[Static Baseline] TraCI error: "
            f"{error}"
        )

    finally:

        try:

            traci.close()

        except Exception:

            pass

        print()

        print(
            "Static baseline simulation finished."
        )

        print(
            f"[Experiment] Results file: "
            f"{RESULTS_FILE}"
        )


if __name__ == "__main__":

    run_simulation()