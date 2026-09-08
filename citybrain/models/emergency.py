from dataclasses import dataclass


@dataclass
class Emergency:
    emergency_id: str
    location: str
    severity: str
    emergency_type: str