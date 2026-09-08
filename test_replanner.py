from citybrain.models.emergency import Emergency
from citybrain.models.plan import EmergencyPlan

from citybrain.planner.emergency_planner import EmergencyPlanner
from citybrain.planner.plan_validator import PlanValidator
from citybrain.planner.replanner import Replanner


# ------------------------------------------------
# Emergency
# ------------------------------------------------

emergency = Emergency(
    emergency_id="ACC_001",
    location="J5",
    severity="HIGH",
    emergency_type="ACCIDENT"
)


# ------------------------------------------------
# Initial city state
# ------------------------------------------------

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
        }
    ],


    "hospitals": [

        {
            "id": "HOSP_02",
            "icu_available": True
        }
    ]
}


# ------------------------------------------------
# Step 1: Create initial plan
# ------------------------------------------------

planner = EmergencyPlanner()

initial_plan = planner.create_plan(
    emergency,
    state
)


print()
print("INITIAL PLAN")
print("------------")

print("Route:", initial_plan.route)
print("ETA:", initial_plan.eta)


# ------------------------------------------------
# Step 2: Validate initial plan
# ------------------------------------------------

validator = PlanValidator()

valid = validator.validate(
    initial_plan,
    state
)

print()
print("Initial plan valid:", valid)


# ------------------------------------------------
# Step 3: Simulate road blockage
# ------------------------------------------------

print()
print("🚧 E2 HAS BECOME BLOCKED")


state["roads"]["E2"]["blocked"] = True


# ------------------------------------------------
# Step 4: Validate again
# ------------------------------------------------

valid = validator.validate(
    initial_plan,
    state
)

print("Plan P0 valid:", valid)


# ------------------------------------------------
# Step 5: Replan
# ------------------------------------------------

if not valid:

    replanner = Replanner()

    new_plan = replanner.replan(
        emergency,
        state
    )


    print()
    print("NEW PLAN P1")
    print("-----------")

    if new_plan:

        print("Route:", new_plan.route)
        print("ETA:", new_plan.eta)

    else:

        print("No alternative plan available.")