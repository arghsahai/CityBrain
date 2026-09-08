import traci


SUMO_BINARY = "sumo"
SUMO_CONFIG = "simulation/network/city.sumocfg"

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


def run_simulation():
    accident_triggered = False

    while traci.simulation.getMinExpectedNumber() > 0:

        current_time = traci.simulation.getTime()

        if current_time >= ACCIDENT_TIME and not accident_triggered:

            print("===================================")
            print("ACCIDENT DETECTED")
            print(f"Time: {current_time} seconds")
            print(f"Road: {ACCIDENT_EDGE}")
            print("Accident event registered")
            print("===================================")

            accident_triggered = True

        traci.simulationStep()

    traci.close()


if __name__ == "__main__":
    start_simulation()
    run_simulation()
