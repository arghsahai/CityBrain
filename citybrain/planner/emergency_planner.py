"""Emergency-plan coordination with legacy and structured result APIs."""

from collections.abc import Mapping
from dataclasses import asdict
from math import isfinite

from citybrain.agents.ambulance_agent import AmbulanceAgent
from citybrain.agents.hospital_agent import HospitalAgent
from citybrain.agents.police_agent import PoliceAgent
from citybrain.agents.signal_agent import SignalAgent
from citybrain.agents.traffic_agent import TrafficAgent
from citybrain.models.plan import EmergencyPlan
from citybrain.models.planner_result import PlannerOutcome, PlanningResult
from citybrain.planner.route_scorer import RouteScore, RouteScorer


class EmergencyPlanner:
    def __init__(self):
        self.traffic_agent = TrafficAgent()
        self.ambulance_agent = AmbulanceAgent()
        self.hospital_agent = HospitalAgent()
        self.signal_agent = SignalAgent()
        self.police_agent = PoliceAgent()
        self.route_scorer = RouteScorer()

    def _score(self, route, state):
        """Use explainable scoring, preserving calculate_score instrumentation."""
        explain = getattr(self.route_scorer, "explain_score", None)
        if callable(explain):
            return explain(route, state)

        # PR #4's ScoreRecorder deliberately exposes calculate_score only.
        value = self.route_scorer.calculate_score(route, state)
        usable = isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)
        eta = self._route_eta(route, state) if usable else None
        return RouteScore(
            usable=usable,
            reason="route_scorable_via_legacy_interface" if usable else "route_unavailable",
            base_travel_time=eta,
            final_score=float(value),
            route=list(route),
        )

    @staticmethod
    def _route_eta(route, state):
        total = 0.0
        roads = state.get("roads", {}) if isinstance(state, Mapping) else {}
        for edge in route:
            road = roads.get(edge, {})
            value = road.get("travel_time") if isinstance(road, Mapping) else None
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value):
                return None
            if value > 0:
                total += value
            elif (value == 0 and road.get("congestion") == "NO_TRAFFIC"
                  and isinstance(road.get("road_length"), (int, float))
                  and isinstance(road.get("speed_limit"), (int, float))
                  and road["road_length"] > 0 and road["speed_limit"] > 0):
                total += road["road_length"] / road["speed_limit"]
            else:
                return None
        return total

    def create_plan(self, emergency, state):
        """Legacy API returning EmergencyPlan or None.

        When PR #4 wraps route_scorer with ScoreRecorder, each route still goes
        through calculate_score exactly once via the compatibility fallback.
        """
        return self.create_plan_result(emergency, state).plan

    def create_plan_result(self, emergency, state):
        """Coordinate agents and return an auditable structured result."""
        if (not isinstance(state, Mapping) or emergency is None
                or not getattr(emergency, "emergency_id", None)):
            return PlanningResult(PlannerOutcome.INVALID_INPUT, "invalid_emergency_or_state")

        traffic = self.traffic_agent.assess(state)
        ambulance = self.ambulance_agent.select(emergency, state)
        if not ambulance.success:
            return PlanningResult(
                PlannerOutcome.NO_RESOURCE, ambulance.reason,
                traffic_assessment=traffic, ambulance_result=ambulance,
            )

        hospital = self.hospital_agent.select(emergency, state)
        if not hospital.success:
            return PlanningResult(
                PlannerOutcome.NO_RESOURCE, hospital.reason,
                traffic_assessment=traffic, ambulance_result=ambulance,
                hospital_result=hospital,
            )

        routes = state.get("routes", {})
        if not isinstance(routes, Mapping) or not routes:
            return PlanningResult(
                PlannerOutcome.NO_ROUTE, "no_candidate_routes",
                traffic_assessment=traffic, ambulance_result=ambulance,
                hospital_result=hospital,
            )

        candidate_scores = {}
        best_route = None
        best_score = float("inf")
        for route_id, route in routes.items():
            score = self._score(route, state)
            candidate_scores[str(route_id)] = score
            if score.usable and score.final_score < best_score:
                best_route, best_score = list(route), score.final_score

        if best_route is None:
            return PlanningResult(
                PlannerOutcome.NO_ROUTE, "all_candidate_routes_unusable",
                traffic_assessment=traffic, ambulance_result=ambulance,
                hospital_result=hospital, candidate_scores=candidate_scores,
            )

        chosen = next(
            score for score in candidate_scores.values()
            if score.usable and score.route == best_route and score.final_score == best_score
        )
        signal = self.signal_agent.recommend(best_route, state)
        police = self.police_agent.recommend(emergency)
        signal_priority = [item.target for item in signal.recommendations]
        recommendations = {
            "traffic": [asdict(item) for item in traffic.assessments],
            "signal": [asdict(item) for item in signal.recommendations],
            "police": [asdict(item) for item in police.recommendations],
        }
        emergency_id = str(emergency.emergency_id)
        if chosen.base_travel_time is None:
            return PlanningResult(
                PlannerOutcome.NO_ROUTE, "selected_route_eta_unavailable",
                traffic_assessment=traffic, ambulance_result=ambulance,
                hospital_result=hospital, candidate_scores=candidate_scores,
            )
        plan = EmergencyPlan(
            ambulance_id=str(ambulance.selected["id"]),
            hospital_id=str(hospital.selected["id"]),
            route=best_route,
            eta=float(chosen.base_travel_time),
            signal_priority=signal_priority,
            plan_id=f"{emergency_id}-P0",
            emergency_id=emergency_id,
            created_time=state.get("simulation_time"),
            recommendations=recommendations,
            status="PROPOSED",
            revision=0,
        )
        return PlanningResult(
            PlannerOutcome.PLAN_CREATED, "emergency_plan_created", plan,
            traffic, ambulance, hospital, candidate_scores,
            recommendations,
            {"selected_score": best_score},
        )

    # Discoverable additive aliases; create_plan remains the compatibility API.
    plan = create_plan_result
    create_structured_plan = create_plan_result
