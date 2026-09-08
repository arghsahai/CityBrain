from citybrain.planner.route_scorer import RouteScorer


state = {

    "roads": {

        "E1": {
            "travel_time": 10,
            "blocked": False,
            "congestion": "HIGH"
        },

        "E2": {
            "travel_time": 12,
            "blocked": False,
            "congestion": "HIGH"
        },

        "E3": {
            "travel_time": 15,
            "blocked": False,
            "congestion": "LOW"
        },

        "E4": {
            "travel_time": 15,
            "blocked": False,
            "congestion": "LOW"
        }
    }
}


routes = {

    "route1": ["E1", "E2"],

    "route2": ["E3", "E4"]
}


scorer = RouteScorer()


print("ROUTE SCORING")
print("-------------")


for route_id, route in routes.items():

    score = scorer.calculate_score(
        route,
        state
    )

    print(route_id, "score =", score)