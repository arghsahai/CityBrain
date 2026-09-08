from citybrain.models.emergency import Emergency
from citybrain.models.plan import EmergencyPlan


emergency = Emergency(
    emergency_id="ACC_001",
    location="J5",
    severity="HIGH",
    emergency_type="ACCIDENT"
)

plan = EmergencyPlan(
    ambulance_id="AMB_01",
    hospital_id="HOSP_01",
    route=["E1", "E3", "E5"],
    eta=42
)

print("Emergency:")
print(emergency)

print("\nEmergency Plan:")
print(plan)