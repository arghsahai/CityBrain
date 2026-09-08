import os
import sys
import traci

from citybrain.core.vehicle_state import VehicleState
from citybrain.core.city_state import CityState


# --------------------------------------------------
# 1. Find SUMO
# --------------------------------------------------

SUMO_HOME = os.environ.get("SUMO_HOME")

if not SUMO_HOME:
    print("ERROR: SUMO_HOME is not set.")
    sys.exit(1)


# --------------------------------------------------
# 2. SUMO configuration
# --------------------------------------------------

CONFIG_FILE = os.path.join(
    "simulation",
    "config",
    "city.sumocfg"
)


# --------------------------------------------------
# 3. SUMO executable
# --------------------------------------------------

SUMO_BINARY = os.path.join(
    SUMO_HOME,
    "bin",
    "sumo-gui.exe"
)


# --------------------------------------------------
# 4. Start SUMO
# --------------------------------------------------

print("Starting SUMO...")

traci.start([
    SUMO_BINARY,
    "-c",
    CONFIG_FILE
])

print("CityBrain connected to SUMO!")


# --------------------------------------------------
# 5. Create central CityState
# --------------------------------------------------

city_state = CityState()


# --------------------------------------------------
# 6. Run simulation
# --------------------------------------------------

for step in range(20):

    # Advance SUMO by one simulation step
    traci.simulationStep()

    # Get all vehicles currently inside SUMO
    vehicle_ids = traci.vehicle.getIDList()

    # Store VehicleState objects for this step
    vehicles = []

    # --------------------------------------------------
    # 7. Read vehicle information from SUMO
    # --------------------------------------------------

    for vehicle_id in vehicle_ids:

        vehicle = VehicleState(
            vehicle_id=vehicle_id,
            edge=traci.vehicle.getRoadID(vehicle_id),
            speed=traci.vehicle.getSpeed(vehicle_id),
            position=traci.vehicle.getPosition(vehicle_id),
            lane=traci.vehicle.getLaneID(vehicle_id),
            acceleration=traci.vehicle.getAcceleration(vehicle_id)
        )

        # Add to temporary list
        vehicles.append(vehicle)

        # Update central CityState
        city_state.update_vehicle(vehicle)


    # --------------------------------------------------
    # 8. Remove vehicles that left the simulation
    # --------------------------------------------------

    current_vehicle_ids = set(vehicle_ids)

    tracked_vehicle_ids = set(city_state.vehicles.keys())

    removed_vehicle_ids = (
        tracked_vehicle_ids - current_vehicle_ids
    )

    for vehicle_id in removed_vehicle_ids:

        city_state.remove_vehicle(vehicle_id)


    # --------------------------------------------------
    # 9. Display current CityState
    # --------------------------------------------------

    print(f"\n===== STEP {step} =====")

    print(
        f"Total vehicles: {city_state.vehicle_count()}"
    )

    print(
        f"CityState contains: "
        f"{city_state.vehicle_count()} vehicles"
    )


    # --------------------------------------------------
    # 10. Display first 3 vehicles
    # --------------------------------------------------

    for vehicle in vehicles[:3]:

        print(f"\n{vehicle}")


# --------------------------------------------------
# 11. Close SUMO
# --------------------------------------------------

traci.close()

print("\nCityBrain simulation finished.")