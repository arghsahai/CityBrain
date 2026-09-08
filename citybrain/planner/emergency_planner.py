from citybrain.agents.traffic_agent import TrafficAgent
from citybrain.agents.ambulance_agent import AmbulanceAgent
from citybrain.agents.hospital_agent import HospitalAgent
from citybrain.agents.signal_agent import SignalAgent
from citybrain.agents.police_agent import PoliceAgent

from citybrain.models.plan import EmergencyPlan
from citybrain.planner.route_scorer import RouteScorer


class EmergencyPlanner:

    def __init__(self):

        self.traffic_agent = TrafficAgent()

        self.ambulance_agent = AmbulanceAgent()

        self.hospital_agent = HospitalAgent()

        self.signal_agent = SignalAgent()

        self.police_agent = PoliceAgent()

        self.route_scorer = RouteScorer()

    def create_plan(self, emergency, state):

        print()
        print(
            "[EmergencyPlanner] "
            "Creating emergency plan..."
        )

        # -------------------------------------------------
        # Traffic agent
        # -------------------------------------------------

        traffic_recommendations = (
            self.traffic_agent.run(state)
        )

        # -------------------------------------------------
        # Ambulance
        # -------------------------------------------------

        ambulance = self.ambulance_agent.run(
            emergency,
            state
        )

        if ambulance is None:

            print(
                "[EmergencyPlanner] "
                "No available ambulance."
            )

            return None

        print(
            "[EmergencyPlanner] "
            f"Ambulance selected: "
            f"{ambulance['id']}"
        )

        # -------------------------------------------------
        # Hospital
        # -------------------------------------------------

        hospital = self.hospital_agent.run(
            emergency,
            state
        )

        if hospital is None:

            print(
                "[EmergencyPlanner] "
                "No hospital available."
            )

            return None

        print(
            "[EmergencyPlanner] "
            f"Hospital selected: "
            f"{hospital['id']}"
        )

        # -------------------------------------------------
        # Routes
        # -------------------------------------------------

        routes = state.get(
            "routes",
            {}
        )

        if not routes:

            print(
                "[EmergencyPlanner] "
                "No candidate routes."
            )

            return None

        best_route = None

        best_score = float("inf")

        # -------------------------------------------------
        # Score every route
        # -------------------------------------------------

        for route_id, route in routes.items():

            score = self.route_scorer.calculate_score(
                route,
                state
            )

            print(
                "[EmergencyPlanner] "
                f"Route {route_id}: "
                f"{route} "
                f"Score={score}"
            )

            if score < best_score:

                best_score = score

                best_route = route

        # -------------------------------------------------
        # No valid route
        # -------------------------------------------------

        if best_route is None:

            print(
                "[EmergencyPlanner] "
                "No valid emergency route found."
            )

            return None

        # -------------------------------------------------
        # Signal priority
        # -------------------------------------------------

        signal_priority = self.signal_agent.run(
            best_route,
            state
        )

        # -------------------------------------------------
        # Police response
        # -------------------------------------------------

        police_response = self.police_agent.run(
            emergency
        )

        # -------------------------------------------------
        # ETA
        # -------------------------------------------------

        eta = 0

        for edge in best_route:

            road = state.get(
                "roads",
                {}
            ).get(
                edge,
                {}
            )

            travel_time = road.get(
                "travel_time",
                float("inf")
            )

            if travel_time == float("inf"):

                print(
                    "[EmergencyPlanner] "
                    "Selected route became invalid."
                )

                return None

            eta += travel_time

        # -------------------------------------------------
        # Create plan
        # -------------------------------------------------

        plan = EmergencyPlan(
            ambulance_id=ambulance["id"],
            hospital_id=hospital["id"],
            route=best_route,
            eta=eta,
            signal_priority=signal_priority
        )

        print(
            "[EmergencyPlanner] "
            "Emergency plan created successfully."
        )

        return plan