from .base_agent import BaseAgent


class HospitalAgent(BaseAgent):

    def __init__(self):
        super().__init__("Hospital Agent")

    def run(self, emergency, state):

        hospitals = state.get("hospitals", [])

        for hospital in hospitals:

            if hospital.get("icu_available"):
                return hospital

        return None