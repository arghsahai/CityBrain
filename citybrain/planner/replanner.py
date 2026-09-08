from citybrain.planner.route_scorer import RouteScorer


class Replanner:

    def __init__(self):

        self.route_scorer = RouteScorer()


    def replan(self, current_plan, state):

        print("REPLANNING EMERGENCY RESPONSE...")


        routes = state.get("routes", {})

        best_route = None
        best_score = float("inf")


        for route_id, route in routes.items():

            score = self.route_scorer.calculate_score(
                route,
                state
            )

            print(
                "Candidate:",
                route_id,
                "Score:",
                score
            )


            # Ignore blocked routes
            if score == float("inf"):
                continue


            if score < best_score:

                best_score = score
                best_route = route


        if best_route is None:

            print("No valid route available.")

            return None


        # Calculate ETA

        eta = 0

        for edge in best_route:

            road = state.get(
                "roads",
                {}
            ).get(
                edge,
                {}
            )

            eta += road.get(
                "travel_time",
                0
            )


        print()
        print("NEW PLAN P1")
        print()
        print("Route:", best_route)
        print("ETA:", eta)


        # Update existing plan

        current_plan.route = best_route
        current_plan.eta = eta


        return current_plan