from .base_agent import BaseAgent


class TrafficAgent(BaseAgent):

    def __init__(self):
        super().__init__("Traffic Agent")

    def run(self, state):
        recommendations = []

        for road_id, road in state.get("roads", {}).items():

            if road.get("congestion") == "HIGH":
                recommendations.append(
                    f"Use an alternative route instead of {road_id}"
                )

        return recommendations