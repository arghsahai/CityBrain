from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmergencyPlan:
    ambulance_id: str
    hospital_id: str
    route: list[str]
    eta: float
    signal_priority: list[str] = field(default_factory=list)
    plan_id: str | None = None
    emergency_id: str | None = None
    created_time: float | None = None
    recommendations: dict[str, Any] = field(default_factory=dict)
    status: str | None = None
    revision: int = 0
    parent_plan_id: str | None = None
