class RouteScorer:

    def calculate_score(self, route, state):

        total_time = 0
        congestion_penalty = 0

        for edge in route:

            road = state.get(
                "roads",
                {}
            ).get(
                edge,
                {}
            )

            # ---------------------------------------------
            # Blocked road
            # ---------------------------------------------

            if road.get("blocked", False):

                return float("inf")

            # ---------------------------------------------
            # Travel time
            # ---------------------------------------------

            travel_time = road.get(
                "travel_time",
                float("inf")
            )

            # No usable travel time
            if travel_time == float("inf"):

                return float("inf")

            total_time += travel_time

            # ---------------------------------------------
            # Congestion penalty
            # ---------------------------------------------

            congestion = road.get(
                "congestion",
                "LOW"
            )

            if congestion == "LOW":

                congestion_penalty += 0

            elif congestion == "MEDIUM":

                congestion_penalty += 5

            elif congestion == "HIGH":

                congestion_penalty += 15

        return (
            total_time
            + congestion_penalty
        )