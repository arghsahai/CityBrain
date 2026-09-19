"""Auditable planner and replanner result contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from citybrain.models.plan import EmergencyPlan


class PlannerOutcome(str, Enum):
    PLAN_CREATED = "PLAN_CREATED"
    KEEP = "KEEP"
    REPLAN = "REPLAN"
    NO_ROUTE = "NO_ROUTE"
    NO_RESOURCE = "NO_RESOURCE"
    INVALID_INPUT = "INVALID_INPUT"


# A decision-oriented name is convenient for policy callers while preserving a
# single enum and a single serialized vocabulary.
PlannerDecision = PlannerOutcome


@dataclass
class PlanningResult:
    outcome: PlannerOutcome
    reason: str
    plan: EmergencyPlan | None = None
    traffic_assessment: Any = None
    ambulance_result: Any = None
    hospital_result: Any = None
    candidate_scores: dict[str, Any] = field(default_factory=dict)
    recommendations: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.outcome is PlannerOutcome.PLAN_CREATED and self.plan is not None


@dataclass
class ReplanProposal:
    proposed_plan: EmergencyPlan | None
    reason: str
    candidate_routes: dict[str, list[str]] = field(default_factory=dict)
    candidate_scores: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplanningResult:
    decision: PlannerOutcome
    reason: str
    current_plan: EmergencyPlan | None
    proposed_plan: EmergencyPlan | None = None
    remaining_route: list[str] = field(default_factory=list)
    candidate_routes: dict[str, list[str]] = field(default_factory=dict)
    candidate_scores: dict[str, Any] = field(default_factory=dict)
    validation_result: Any = None
    current_score: float = float("inf")
    proposed_score: float = float("inf")
    improvement: float | None = None
    threshold: float = 0.0
    commitment_satisfied: bool = True
    cooldown_satisfied: bool = True
    accepted_plan: EmergencyPlan | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def outcome(self) -> PlannerOutcome:
        return self.decision

    @property
    def current_plan_id(self) -> str | None:
        return self.current_plan.plan_id if self.current_plan else None

    @property
    def proposed_plan_id(self) -> str | None:
        return self.proposed_plan.plan_id if self.proposed_plan else None

    @property
    def current_route(self) -> list[str]:
        return list(self.current_plan.route) if self.current_plan else []


PlannerResult = PlanningResult
PlanningOutcome = PlannerOutcome
ReplannerResult = ReplanningResult
