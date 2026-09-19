"""Route proposal, policy decision and explicit acceptance lifecycle."""

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
from math import isfinite

from citybrain.agents.signal_agent import SignalAgent
from citybrain.models.plan import EmergencyPlan
from citybrain.models.planner_result import (
    PlannerOutcome,
    ReplanProposal,
    ReplanningResult,
)
from citybrain.planner.plan_validator import PlanValidator
from citybrain.planner.replanning_policy import ReplanningPolicy
from citybrain.planner.route_scorer import RouteScore, RouteScorer


class Replanner:
    def __init__(self, policy=None, validator=None):
        self.route_scorer = RouteScorer()
        self.policy = policy or ReplanningPolicy()
        self.validator = validator or PlanValidator()
        self.signal_agent = SignalAgent()
        self.active_plan = None
        self.active_since = None
        self.last_replan_time = None

    def replan(self, current_plan, state):
        """Legacy API: select a route and mutate the supplied plan in place.

        This compatibility behavior is used by PR #4. It intentionally does not
        apply ReplanningPolicy because the validated runtime owns its own gate.
        Physical execution remains outside this class.
        """
        routes = state.get("routes", {}) if isinstance(state, Mapping) else {}
        best_route = None
        best_score = float("inf")
        for route in routes.values() if isinstance(routes, Mapping) else ():
            score = self.route_scorer.calculate_score(route, state)
            if score < best_score:
                best_score = score
                best_route = list(route)
        if best_route is None or current_plan is None:
            return None

        eta = self._route_eta(best_route, state)
        if eta is None:
            return None
        current_plan.route = best_route
        current_plan.eta = eta
        return current_plan

    def propose(self, current_plan, state, *, current_time=None):
        """Propose the best usable candidate without mutating current_plan."""
        routes = state.get("routes", {}) if isinstance(state, Mapping) else {}
        if not isinstance(routes, Mapping) or not routes:
            return ReplanProposal(None, "no_candidate_routes")

        candidate_routes = {}
        candidate_scores = {}
        best_route = None
        best_score = float("inf")
        best_result = None
        for route_id, route in routes.items():
            route_copy = list(route) if isinstance(route, (list, tuple)) else []
            candidate_routes[str(route_id)] = route_copy
            result = self._explain(route, state)
            candidate_scores[str(route_id)] = result
            if result.usable and result.final_score < best_score:
                best_route = route_copy
                best_score = result.final_score
                best_result = result

        if best_route is None or best_result is None:
            return ReplanProposal(
                None, "all_candidate_routes_unusable", candidate_routes,
                candidate_scores,
            )
        if current_plan is None or not all(
            hasattr(current_plan, field)
            for field in ("ambulance_id", "hospital_id", "route", "eta")
        ):
            return ReplanProposal(
                None, "invalid_current_plan", candidate_routes, candidate_scores,
            )

        revision = getattr(current_plan, "revision", 0) + 1
        emergency_id = getattr(current_plan, "emergency_id", None)
        current_plan_id = getattr(current_plan, "plan_id", None)
        plan_id = f"{emergency_id}-P{revision}" if emergency_id else (
            f"{current_plan_id}-P{revision}" if current_plan_id else f"P{revision}"
        )
        if best_result.base_travel_time is None:
            return ReplanProposal(
                None, "candidate_eta_unavailable", candidate_routes, candidate_scores,
            )
        signal = self.signal_agent.recommend(best_route, state)
        signal_priority = [item.target for item in signal.recommendations]
        recommendations = deepcopy(getattr(current_plan, "recommendations", {}))
        recommendations["signal"] = [
            {
                "target": item.target,
                "action": item.action,
                "reason": item.reason,
                "advisory": item.advisory,
            }
            for item in signal.recommendations
        ]
        proposed = EmergencyPlan(
            ambulance_id=current_plan.ambulance_id,
            hospital_id=current_plan.hospital_id,
            route=best_route,
            eta=float(best_result.base_travel_time),
            signal_priority=signal_priority,
            plan_id=plan_id,
            emergency_id=emergency_id,
            created_time=current_time if current_time is not None else state.get("simulation_time"),
            recommendations=recommendations,
            status="PROPOSED",
            revision=revision,
            parent_plan_id=current_plan_id,
        )
        return ReplanProposal(
            proposed, "usable_candidate_proposed", candidate_routes,
            candidate_scores,
        )

    def replan_structured(
        self,
        current_plan,
        state,
        *,
        remaining_route=None,
        current_time=None,
        active_since=None,
        last_replan_time=None,
        policy=None,
    ):
        """Return a KEEP/REPLAN/NO_ROUTE decision without accepting/executing it."""
        selected_route = (
            list(remaining_route) if remaining_route is not None
            else list(getattr(current_plan, "route", []))
        )
        validation = self.validator.validate_structured(
            current_plan, state, remaining_route=selected_route,
        )
        proposal = self.propose(current_plan, state, current_time=current_time)
        current_score_result = self._explain(selected_route, state)
        current_score = current_score_result.final_score

        proposed_score = float("inf")
        proposed_route = []
        if proposal.proposed_plan is not None:
            proposed_route = proposal.proposed_plan.route
            for route_id, route in proposal.candidate_routes.items():
                if route == proposed_route:
                    proposed_score = proposal.candidate_scores[route_id].final_score
                    break

        policy_result = (policy or self.policy).decide(
            validation=validation,
            current_route=selected_route,
            proposed_route=proposed_route,
            current_score=current_score,
            proposed_score=proposed_score,
            current_time=current_time,
            active_since=self.active_since if active_since is None else active_since,
            last_replan_time=(
                self.last_replan_time if last_replan_time is None else last_replan_time
            ),
        )
        return ReplanningResult(
            decision=policy_result.decision,
            reason=policy_result.reason,
            current_plan=current_plan,
            proposed_plan=proposal.proposed_plan,
            remaining_route=selected_route,
            candidate_routes=proposal.candidate_routes,
            candidate_scores=proposal.candidate_scores,
            validation_result=validation,
            current_score=current_score,
            proposed_score=proposed_score,
            improvement=policy_result.improvement,
            threshold=policy_result.threshold,
            commitment_satisfied=policy_result.commitment_satisfied,
            cooldown_satisfied=policy_result.cooldown_satisfied,
            metadata={"proposal_reason": proposal.reason},
        )

    structured_replan = replan_structured
    evaluate = replan_structured
    propose_replan = propose

    def set_active_plan(self, plan, *, accepted_time=None):
        """Explicitly register an already accepted plan as the lifecycle base."""
        self.active_plan = deepcopy(plan)
        self.active_plan.status = "ACTIVE"
        self.active_since = accepted_time
        return self.active_plan

    def accept(self, result, *, accepted_time=None):
        """Accept a REPLAN proposal; physical route application is still external."""
        if result.decision is not PlannerOutcome.REPLAN or result.proposed_plan is None:
            raise ValueError("only a REPLAN result with a proposal can be accepted")
        accepted = replace(
            result.proposed_plan,
            route=list(result.proposed_plan.route),
            signal_priority=list(result.proposed_plan.signal_priority),
            recommendations=deepcopy(result.proposed_plan.recommendations),
            status="ACTIVE",
        )
        self.active_plan = accepted
        self.active_since = accepted_time
        self.last_replan_time = accepted_time
        result.accepted_plan = accepted
        return accepted

    accept_plan = accept

    def evaluate_active(self, state, **kwargs):
        if self.active_plan is None:
            raise ValueError("no active plan has been registered")
        return self.replan_structured(self.active_plan, state, **kwargs)

    def _explain(self, route, state):
        explain = getattr(self.route_scorer, "explain_score", None)
        if callable(explain):
            return explain(route, state)
        score = self.route_scorer.calculate_score(route, state)
        usable = isinstance(score, (int, float)) and not isinstance(score, bool) and isfinite(score)
        return RouteScore(
            usable, "route_scorable_via_legacy_interface" if usable else "route_unavailable",
            self._route_eta(route, state) if usable else None,
            final_score=float(score), route=list(route),
        )

    @staticmethod
    def _route_eta(route, state):
        result = RouteScorer().explain_score(route, state)
        return result.base_travel_time if result.usable else None
