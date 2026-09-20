"""CityBrain runtime event types and data model."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):
    """Meaningful runtime events detected by comparing CityState snapshots."""

    ACCIDENT_DETECTED = "ACCIDENT_DETECTED"
    ROAD_BLOCKED = "ROAD_BLOCKED"
    ROAD_UNBLOCKED = "ROAD_UNBLOCKED"
    CONGESTION_CHANGED = "CONGESTION_CHANGED"
    AMBULANCE_STATE_CHANGED = "AMBULANCE_STATE_CHANGED"
    ROUTE_INVALIDATED = "ROUTE_INVALIDATED"
    VEHICLE_ARRIVED = "VEHICLE_ARRIVED"
    VEHICLE_TELEPORTED = "VEHICLE_TELEPORTED"
    VEHICLE_DEPARTED = "VEHICLE_DEPARTED"


@dataclass
class CityBrainEvent:
    """
    Structured runtime event.

    Events report observable changes.  They do NOT decide how
    the planner should respond.
    """

    event_type: EventType
    simulation_time: float
    data: Dict[str, Any] = field(default_factory=dict)
    entity_id: Optional[str] = None
    reason: Optional[str] = None