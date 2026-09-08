from dataclasses import dataclass, field


@dataclass
class EmergencyPlan:
    ambulance_id: str
    hospital_id: str
    route: list[str]
    eta: float
    signal_priority: list[str] = field(default_factory=list)