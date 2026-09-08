from citybrain.agents.police_agent import PoliceAgent
from citybrain.models.emergency import Emergency


emergency = Emergency(
    emergency_id="ACC_001",
    location="J5",
    severity="HIGH",
    emergency_type="ACCIDENT"
)


agent = PoliceAgent()

result = agent.run(emergency)

print("Police Agent:")
print("Emergency:", result["emergency_id"])
print("Location:", result["location"])
print("Action:", result["action"])