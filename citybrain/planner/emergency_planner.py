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

        # -----------------------------------------
        # 1. Analyze traffic
        # -----------------------------------------

        traffic_recommendations = self.traffic_agent.run(state)


        # -----------------------------------------
        # 2. Select ambulance
        # -----------------------------------------

        ambulance = self.ambulance_agent.run(
            emergency,
            state
        )

        if ambulance is None:
            return None


        # -----------------------------------------
        # 3. Select hospital
        # -----------------------------------------

        hospital = self.hospital_agent.run(
            emergency,
            state
        )

        if hospital is None:
            return None


        # -----------------------------------------
        # 4. Get candidate routes
        # -----------------------------------------

        routes = state.get("routes", {})

        if not routes:
            return None


        # -----------------------------------------
        # 5. Score every route
        # -----------------------------------------

        best_route = None
        best_score = float("inf")


        for route_id, route in routes.items():

            score = self.route_scorer.calculate_score(
                route,
                state
            )

            print(
                "Route:",
                route_id,
                "Score:",
                score
            )


            if score < best_score:

                best_score = score
                best_route = route


        # -----------------------------------------
        # 6. Check if a route exists
        # -----------------------------------------

        if best_route is None:
            return None


        # -----------------------------------------
        # 7. Signal priority
        # -----------------------------------------

        signal_priority = self.signal_agent.run(
            best_route,
            state
        )


        # -----------------------------------------
        # 8. Police response
        # -----------------------------------------

        police_response = self.police_agent.run(
            emergency
        )


        # -----------------------------------------
        # 9. Calculate ETA
        # -----------------------------------------

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


        # -----------------------------------------
        # 10. Create EmergencyPlan
        # -----------------------------------------

        plan = EmergencyPlan(

            ambulance_id=ambulance["id"],

            hospital_id=hospital["id"],

            route=best_route,

            eta=eta,

            signal_priority=signal_priority
        )


        return plan