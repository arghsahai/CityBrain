from citybrain.agents.hospital_agent import HospitalAgent
from citybrain.models.emergency import Emergency


emergency = Emergency(
    emergency_id="ACC_001",
    location="J5",
    severity="HIGH",
    emergency_type="ACCIDENT"
)


state = {
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


agent = HospitalAgent()

hospital = agent.run(emergency, state)

print("Hospital Agent:")

if hospital:
    print("Selected hospital:", hospital["id"])
else:
    print("No suitable hospital available")