from citybrain.models.emergency import Emergency
from citybrain.planner.emergency_planner import EmergencyPlanner


# Emergency
emergency = Emergency(
    emergency_id="ACC_001",
    location="J5",
    severity="HIGH",
    emergency_type="ACCIDENT"
)


# Simulated CityState
state = {

    "roads": {

        "E1": {
            "from": "J1",
            "to": "J2",
            "blocked": False,
            "travel_time": 10
        },

        "E2": {
            "from": "J2",
            "to": "J3",
            "blocked": False,
            "travel_time": 12
        },

        "E3": {
            "from": "J4",
            "to": "J5",
            "blocked": False,
            "travel_time": 15
        },

        "E4": {
            "from": "J5",
            "to": "J6",
            "blocked": False,
            "travel_time": 15
        }
    },


    "routes": {

        "route1": [
            "E1",
            "E2"
        ],

        "route2": [
            "E3",
            "E4"
        ]
    },


    "ambulances": [

        {
            "id": "AMB_01",
            "available": True
        },

        {
            "id": "AMB_02",
            "available": False
        }
    ],


    "hospitals": [

        {
            "id": "HOSP_01",
            "icu_available": False
        },

        {
            "id": "HOSP_02",
            "icu_available": True
        }
    ]
}


# Create planner
planner = EmergencyPlanner()


# Generate plan
plan = planner.create_plan(
    emergency,
    state
)


print("GLOBAL EMERGENCY PLANNER")
print("------------------------")


if plan:

    print("Ambulance:", plan.ambulance_id)
    print("Hospital:", plan.hospital_id)
    print("Route:", plan.route)
    print("ETA:", plan.eta, "seconds")
    print("Signal Priority:", plan.signal_priority)

else:

    print("No emergency plan could be created.")