from citybrain.models.plan import EmergencyPlan
from citybrain.planner.plan_validator import PlanValidator


# Existing emergency plan
plan = EmergencyPlan(
    ambulance_id="AMB_01",
    hospital_id="HOSP_02",
    route=["E1", "E2"],
    eta=22,
    signal_priority=["J2", "J3"]
)


# Current city state
state = {

    "roads": {

        "E1": {
            "blocked": False
        },

        "E2": {
            "blocked": False
        }
    }
}


validator = PlanValidator()


# First validation
result = validator.validate(plan, state)

print("PLAN VALIDATOR")
print("--------------")
print("Initial plan valid:", result)


# Simulate road blockage
state["roads"]["E2"]["blocked"] = True


# Validate again
result = validator.validate(plan, state)

print("After E2 blockage:", result)