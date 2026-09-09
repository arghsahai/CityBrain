import os
import sys
import traci

from citybrain.core.vehicle_state import VehicleState
from citybrain.core.city_state import CityState
from citybrain.core.traffic_perception import build_road_state


# ============================================================
# 1. FIND SUMO
# ============================================================

SUMO_HOME = os.environ.get("SUMO_HOME")

if not SUMO_HOME:
    print("ERROR: SUMO_HOME is not set.")
    sys.exit(1)


# ============================================================
# 2. SUMO CONFIGURATION
# ============================================================

CONFIG_FILE = os.path.join(
    "simulation",
    "config",
    "city.sumocfg"
)


# ============================================================
# 3. SUMO EXECUTABLE
# ============================================================

SUMO_BINARY = os.path.join(
    SUMO_HOME,
    "bin",
    "sumo-gui.exe"
)


# ============================================================
# 4. START SUMO
# ============================================================

print("\nStarting SUMO...")

traci.start([
    SUMO_BINARY,
    "-c",
    CONFIG_FILE
])

print("CityBrain connected to SUMO!")


# ============================================================
# 5. CREATE CENTRAL CITY STATE
# ============================================================

city_state = CityState()


# ============================================================
# 6. GET ROAD IDs
# ============================================================

road_ids = traci.edge.getIDList()

# Remove SUMO internal junction edges
road_ids = [
    road_id
    for road_id in road_ids
    if not road_id.startswith(":")
]


# ============================================================
# 7. RUN SIMULATION
# ============================================================

for step in range(20):

    # --------------------------------------------------------
    # Advance SUMO by one simulation step
    # --------------------------------------------------------

    traci.simulationStep()


    # ========================================================
    # VEHICLE STATE
    # ========================================================

    vehicle_ids = traci.vehicle.getIDList()

    vehicles = []


    # --------------------------------------------------------
    # Read vehicle information from SUMO
    # --------------------------------------------------------

    for vehicle_id in vehicle_ids:

        vehicle = VehicleState(
            vehicle_id=vehicle_id,
            edge=traci.vehicle.getRoadID(vehicle_id),
            speed=traci.vehicle.getSpeed(vehicle_id),
            position=traci.vehicle.getPosition(vehicle_id),
            lane=traci.vehicle.getLaneID(vehicle_id),
            acceleration=traci.vehicle.getAcceleration(vehicle_id)
        )

        vehicles.append(vehicle)

        # Store/update vehicle in CityState
        city_state.update_vehicle(vehicle)


    # ========================================================
    # REMOVE VEHICLES THAT LEFT THE SIMULATION
    # ========================================================

    current_vehicle_ids = set(vehicle_ids)

    tracked_vehicle_ids = set(
        city_state.vehicles.keys()
    )

    removed_vehicle_ids = (
        tracked_vehicle_ids - current_vehicle_ids
    )

    for vehicle_id in removed_vehicle_ids:

        city_state.remove_vehicle(vehicle_id)


    # ========================================================
    # ROAD STATE
    # ========================================================

    for road_id in road_ids:

        try:

            road_state = build_road_state(
                traci,
                road_id
            )

            city_state.update_road(road_state)

        except Exception as e:

            print(
                f"Could not read road {road_id}: {e}"
            )


    # ========================================================
    # CITY LEVEL STATISTICS
    # ========================================================

    # Calculate average speed of all vehicles
    if vehicles:

        average_vehicle_speed = (
            sum(vehicle.speed for vehicle in vehicles)
            / len(vehicles)
        )

    else:

        average_vehicle_speed = 0.0


    # Count roads according to congestion level
    high_congestion_roads = 0
    medium_congestion_roads = 0
    low_congestion_roads = 0

    for road in city_state.roads.values():

        if road.congestion == "HIGH":

            high_congestion_roads += 1

        elif road.congestion == "MEDIUM":

            medium_congestion_roads += 1

        elif road.congestion == "LOW":

            low_congestion_roads += 1


    # ========================================================
    # DISPLAY CITYBRAIN STATE
    # ========================================================

    print("\n")
    print("=" * 70)
    print("                    CITYBRAIN SIMULATION")
    print(f"                           STEP {step}")
    print("=" * 70)


    # ========================================================
    # CITY SUMMARY
    # ========================================================

    print("\nCITY SUMMARY")
    print("-" * 70)

    print(
        f"  Vehicles currently in simulation : "
        f"{city_state.vehicle_count()}"
    )

    print(
        f"  Roads currently tracked          : "
        f"{city_state.road_count()}"
    )

    print(
        f"  Average vehicle speed            : "
        f"{average_vehicle_speed:.2f} m/s"
    )

    print(
        f"  HIGH congestion roads            : "
        f"{high_congestion_roads}"
    )

    print(
        f"  MEDIUM congestion roads          : "
        f"{medium_congestion_roads}"
    )

    print(
        f"  LOW congestion roads             : "
        f"{low_congestion_roads}"
    )


    # ========================================================
    # VEHICLE STATES
    # ========================================================

    print("\nVEHICLE STATES")
    print("-" * 70)

    # We only DISPLAY the first 3 vehicles.
    # CityState still stores ALL vehicles.

    for vehicle in vehicles[:3]:

        print(
            f"  ID: {vehicle.vehicle_id:<10} | "
            f"Edge: {vehicle.edge:<6} | "
            f"Speed: {vehicle.speed:>6.2f} m/s | "
            f"Lane: {vehicle.lane}"
        )

        print(
            f"       Position: "
            f"({vehicle.position[0]:>7.2f}, "
            f"{vehicle.position[1]:>7.2f}) | "
            f"Acceleration: "
            f"{vehicle.acceleration:>6.2f} m/s²"
        )


    # ========================================================
    # ROAD STATES
    # ========================================================

    print("\nROAD STATES")
    print("-" * 70)

    print(
        f"  {'Road':<8}"
        f"{'Vehicles':>10}"
        f"{'Avg Speed':>13}"
        f"{'Occupancy':>13}"
        f"{'Travel Time':>15}"
        f"{'Congestion':>14}"
    )

    print("-" * 70)


    # Display first 5 roads
    for road_id, road in list(
        city_state.roads.items()
    )[:5]:

        if road.travel_time == float("inf"):

            travel_time = "INF"

        else:

            travel_time = f"{road.travel_time:.2f} s"


        print(
            f"  {road.road_id:<8}"
            f"{road.vehicle_count:>10}"
            f"{road.average_speed:>13.2f}"
            f"{road.occupancy:>13.2f}"
            f"{travel_time:>15}"
            f"{road.congestion:>14}"
        )


    print("=" * 70)


# ============================================================
# 8. CLOSE SUMO
# ============================================================

traci.close()

print("\nCityBrain simulation finished.")