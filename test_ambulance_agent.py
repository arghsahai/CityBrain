from citybrain.agents.ambulance_agent import AmbulanceAgent
from citybrain.models.emergency import Emergency


emergency = Emergency(
    emergency_id="ACC_001",
    location="J5",
    severity="HIGH",
    emergency_type="ACCIDENT"
)


state = {
    "ambulances": [
        {
            "id": "AMB_01",
            "available": True
        },
        {
            "id": "AMB_02",
            "available": False
        }
    ]
}


agent = AmbulanceAgent()

ambulance = agent.run(emergency, state)

print("Ambulance Agent:")

if ambulance:
    print("Selected ambulance:", ambulance["id"])
else:
    print("No ambulance available")