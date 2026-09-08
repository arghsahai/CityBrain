import traci


SUMO_BINARY = "sumo"
SUMO_CONFIG = "simulation/scenarios/S02_accident/S02.sumocfg"

ACCIDENT_TIME = 300
ACCIDENT_EDGE = "E3"


def start_simulation():
    traci.start([
        SUMO_BINARY,
        "-c",
        SUMO_CONFIG,
        "--step-length",
        "1"
    ])


def get_road_state(edge_id):
    vehicle_ids = traci.edge.getLastStepVehicleIDs(edge_id)
    vehicle_count = len(vehicle_ids)

    mean_speed = traci.edge.getLastStepMeanSpeed(edge_id)
    occupancy = traci.edge.getLastStepOccupancy(edge_id)

    return vehicle_count, mean_speed, occupancy


def run_simulation():

    accident_triggered = False

    while traci.simulation.getMinExpectedNumber() > 0:

        current_time = traci.simulation.getTime()

        # Accident event
        if current_time >= ACCIDENT_TIME and not accident_triggered:

            print("\n===================================")
            print("ACCIDENT DETECTED")
            print(f"Time: {current_time} seconds")
            print(f"Road: {ACCIDENT_EDGE}")
            print("===================================")

            accident_triggered = True

        # Monitor accident road
        if accident_triggered and current_time % 30 == 0:

            vehicle_count, mean_speed, occupancy = get_road_state(
                ACCIDENT_EDGE
            )

            print(
                f"[{current_time:.0f}s] "
                f"E3 vehicles={vehicle_count}, "
                f"speed={mean_speed:.2f} m/s, "
                f"occupancy={occupancy:.2f}%"
            )

        traci.simulationStep()

    traci.close()


if __name__ == "__main__":
    start_simulation()
    run_simulation()