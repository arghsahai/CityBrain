"""Planner-level replanning policy, intentionally separate from runtime gates."""

from dataclasses import dataclass
from math import isfinite

from citybrain.models.planner_result import PlannerOutcome


def _finite_score(value):
    try:
        return not isinstance(value, bool) and isfinite(value)
    except TypeError:
        return False


@dataclass(frozen=True)
class ReplanningPolicyConfig:
    minimum_improvement: float = 0.0
    minimum_commitment: float = 0.0
    cooldown: float = 0.0
    invalid_route_override: bool = True

    def __post_init__(self):
        for name in ("minimum_improvement", "minimum_commitment", "cooldown"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")


@dataclass(frozen=True)
class PolicyDecision:
    decision: PlannerOutcome
    reason: str
    improvement: float | None
    threshold: float
    commitment_satisfied: bool
    cooldown_satisfied: bool

    @property
    def outcome(self):
        return self.decision


class ReplanningPolicy:
    """Choose KEEP, REPLAN or NO_ROUTE without executing a route change."""

    def __init__(
        self,
        minimum_improvement=0.0,
        minimum_commitment=0.0,
        cooldown=0.0,
        invalid_route_override=True,
        *,
        config=None,
    ):
        self.config = config or ReplanningPolicyConfig(
            minimum_improvement=minimum_improvement,
            minimum_commitment=minimum_commitment,
            cooldown=cooldown,
            invalid_route_override=invalid_route_override,
        )

    def decide(
        self,
        *,
        validation,
        current_route,
        proposed_route,
        current_score,
        proposed_score,
        current_time=None,
        active_since=None,
        last_replan_time=None,
    ):
        commitment_satisfied = self._elapsed(
            current_time, active_since, self.config.minimum_commitment,
        )
        cooldown_satisfied = self._elapsed(
            current_time, last_replan_time, self.config.cooldown,
        )

        if not proposed_route or not _finite_score(proposed_score):
            return PolicyDecision(
                PlannerOutcome.NO_ROUTE, "no_usable_candidate_route", None,
                self.config.minimum_improvement, commitment_satisfied,
                cooldown_satisfied,
            )

        invalid = validation is not None and not validation.valid
        if invalid and self.config.invalid_route_override:
            return PolicyDecision(
                PlannerOutcome.REPLAN,
                f"invalid_active_route_override:{validation.reason}",
                self._improvement(current_score, proposed_score),
                self.config.minimum_improvement, True, True,
            )

        improvement = self._improvement(current_score, proposed_score)
        if list(proposed_route) == list(current_route):
            return PolicyDecision(
                PlannerOutcome.KEEP, "best_candidate_matches_active_route",
                improvement, self.config.minimum_improvement,
                commitment_satisfied, cooldown_satisfied,
            )
        if improvement is None or improvement < self.config.minimum_improvement:
            return PolicyDecision(
                PlannerOutcome.KEEP, "improvement_below_threshold", improvement,
                self.config.minimum_improvement, commitment_satisfied,
                cooldown_satisfied,
            )
        if not commitment_satisfied:
            return PolicyDecision(
                PlannerOutcome.KEEP, "minimum_commitment_not_elapsed", improvement,
                self.config.minimum_improvement, False, cooldown_satisfied,
            )
        if not cooldown_satisfied:
            return PolicyDecision(
                PlannerOutcome.KEEP, "cooldown_not_elapsed", improvement,
                self.config.minimum_improvement, True, False,
            )
        return PolicyDecision(
            PlannerOutcome.REPLAN, "material_improvement_and_timing_satisfied",
            improvement, self.config.minimum_improvement, True, True,
        )

    evaluate = decide

    @staticmethod
    def _elapsed(now, since, threshold):
        if threshold == 0 or now is None or since is None:
            return True
        return now - since >= threshold

    @staticmethod
    def _improvement(current_score, proposed_score):
        if not _finite_score(proposed_score):
            return None
        if current_score == float("inf"):
            return float("inf")
        if not _finite_score(current_score):
            return None
        return current_score - proposed_score
