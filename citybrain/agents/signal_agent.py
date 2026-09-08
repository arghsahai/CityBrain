from .base_agent import BaseAgent


class SignalAgent(BaseAgent):

    def __init__(self):
        super().__init__("Traffic Signal Agent")

    def run(self, route, state):

        intersections = []

        for edge in route:

            road = state.get("roads", {}).get(edge)

            if road and road.get("to"):
                intersections.append(road["to"])

        return intersections