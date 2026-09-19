from .base_agent import BaseAgent
from collections.abc import Mapping

from citybrain.models.agent_result import RoadAssessment, TrafficAssessmentResult


class TrafficAgent(BaseAgent):

    def __init__(self):
        super().__init__("Traffic Agent")

    def run(self, state):
        """Legacy list-of-strings interface."""
        recommendations = []

        for road_id, road in state.get("roads", {}).items():

            if road.get("congestion") == "HIGH":
                recommendations.append(
                    f"Use an alternative route instead of {road_id}"
                )

        return recommendations

    def assess(self, state):
        """Return supplied congestion as structured, advisory assessments."""
        roads = state.get("roads", {}) if isinstance(state, Mapping) else {}
        if not isinstance(roads, Mapping):
            return TrafficAssessmentResult(reason="invalid_road_mapping")

        assessments = []
        recommendations = []
        for road_id, road in roads.items():
            congestion = road.get("congestion") if isinstance(road, Mapping) else None
            if congestion == "HIGH":
                assessment = "CONGESTED"
                recommendation = f"Use an alternative route instead of {road_id}"
                reason = "supplied_high_congestion"
                recommendations.append(recommendation)
            elif congestion == "MEDIUM":
                assessment = "DELAYED"
                recommendation = f"Monitor delay on {road_id}"
                reason = "supplied_medium_congestion"
            elif congestion in ("LOW", "NO_TRAFFIC"):
                assessment = "PASSABLE"
                recommendation = f"No congestion diversion advised for {road_id}"
                reason = f"supplied_{congestion.lower()}"
            else:
                assessment = "UNKNOWN"
                recommendation = f"Treat congestion on {road_id} as unknown"
                reason = "congestion_not_supplied_or_unknown"
            assessments.append(RoadAssessment(
                road_id=str(road_id), congestion=congestion, assessment=assessment,
                recommendation=recommendation, reason=reason,
            ))
        return TrafficAssessmentResult(assessments, recommendations)

    run_structured = assess
    analyze = assess
