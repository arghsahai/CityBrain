class RouteScorer:

    def calculate_score(self, route, state):

        total_time = 0
        congestion_penalty = 0

        for edge in route:

            road = state.get("roads", {}).get(edge, {})

            # Skip blocked routes
            if road.get("blocked", False):
                return float("inf")

            # Travel time
            total_time += road.get("travel_time", 0)

            # Congestion penalty
            congestion = road.get("congestion", "LOW")

            if congestion == "LOW":
                congestion_penalty += 0

            elif congestion == "MEDIUM":
                congestion_penalty += 5

            elif congestion == "HIGH":
                congestion_penalty += 15

        return total_time + congestion_penalty