"""Structured, advisory-only results returned by planner agents."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RoadAssessment:
    road_id: str
    congestion: str | None
    assessment: str
    recommendation: str
    reason: str


@dataclass
class TrafficAssessmentResult:
    assessments: list[RoadAssessment] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    reason: str = "traffic_assessed"


@dataclass
class ResourceSelectionResult:
    selected: dict[str, Any] | None
    success: bool
    reason: str
    resource_type: str
    considered: int = 0


@dataclass(frozen=True)
class AdvisoryRecommendation:
    target: str
    action: str
    reason: str
    advisory: bool = True


@dataclass
class AdvisoryResult:
    recommendations: list[AdvisoryRecommendation] = field(default_factory=list)
    reason: str = "advisory_recommendations_created"
    advisory_only: bool = True
