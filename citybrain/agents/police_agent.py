from .base_agent import BaseAgent


class PoliceAgent(BaseAgent):

    def __init__(self):
        super().__init__("Police Agent")

    def run(self, emergency):

        return {
            "emergency_id": emergency.emergency_id,
            "location": emergency.location,
            "action": "ACCIDENT_RESPONSE_REQUIRED"
        }