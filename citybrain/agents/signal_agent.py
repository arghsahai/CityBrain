from .base_agent import BaseAgent
from collections.abc import Mapping

from citybrain.models.agent_result import AdvisoryRecommendation, AdvisoryResult


class SignalAgent(BaseAgent):

    def __init__(self):
        super().__init__("Traffic Signal Agent")

    def run(self, route, state):
        """Legacy junction-list interface; this performs no signal actuation."""

        intersections = []

        for edge in route:

            road = state.get("roads", {}).get(edge)

            if road and road.get("to"):
                intersections.append(road["to"])

        return intersections

    def recommend(self, route, state):
        """Create advisory priority requests without claiming execution."""
        roads = state.get("roads", {}) if isinstance(state, Mapping) else {}
        recommendations = []
        if not isinstance(route, (list, tuple)) or not isinstance(roads, Mapping):
            return AdvisoryResult([], "invalid_route_or_road_mapping")
        for edge in route:
            road = roads.get(edge)
            if isinstance(road, Mapping) and road.get("to"):
                recommendations.append(AdvisoryRecommendation(
                    target=str(road["to"]), action="REQUEST_SIGNAL_PRIORITY",
                    reason=f"junction_follows_route_edge:{edge}",
                ))
        reason = "signal_priority_advisories_created" if recommendations else "no_route_junctions_available"
        return AdvisoryResult(recommendations, reason)

    run_structured = recommend
    recommend_priority = recommend
