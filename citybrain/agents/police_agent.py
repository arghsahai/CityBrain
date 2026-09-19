from .base_agent import BaseAgent

from citybrain.models.agent_result import AdvisoryRecommendation, AdvisoryResult


class PoliceAgent(BaseAgent):

    def __init__(self):
        super().__init__("Police Agent")

    def run(self, emergency):

        return {
            "emergency_id": emergency.emergency_id,
            "location": emergency.location,
            "action": "ACCIDENT_RESPONSE_REQUIRED"
        }

    def recommend(self, emergency):
        """Create a logical response advisory without claiming dispatch."""
        emergency_id = getattr(emergency, "emergency_id", None)
        location = getattr(emergency, "location", None)
        if not emergency_id or not location:
            return AdvisoryResult([], "invalid_emergency_for_police_advisory")
        recommendation = AdvisoryRecommendation(
            target=str(location), action="ACCIDENT_RESPONSE_REQUIRED",
            reason=f"logical_response_for_emergency:{emergency_id}",
        )
        return AdvisoryResult([recommendation], "police_response_advisory_created")

    run_structured = recommend
    recommend_response = recommend
