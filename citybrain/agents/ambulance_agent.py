from .base_agent import BaseAgent


class AmbulanceAgent(BaseAgent):

    def __init__(self):
        super().__init__("Ambulance Agent")

    def run(self, emergency, state):

        ambulances = state.get("ambulances", [])

        for ambulance in ambulances:

            if ambulance.get("available"):
                return ambulance

        return None