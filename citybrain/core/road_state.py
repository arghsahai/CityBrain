"""Canonical representation of one SUMO road/edge at a point in time."""

from dataclasses import dataclass


# Road measurement status constants.
MEASURED = "MEASURED"
EMPTY = "EMPTY"
BLOCKED = "BLOCKED"
UNKNOWN = "UNKNOWN"


@dataclass
class RoadState:
    """
    Current observed state of one SUMO road/edge.

    SUMO remains the source of truth.  Measurement status
    distinguishes the quality of the observation.

    Measurement status semantics:

        MEASURED    At least one vehicle is on the road; speed and
                    occupancy reflect live traffic.

        EMPTY       No vehicles are present.  The road is passable
                    but speed/occupancy are physical defaults, not
                    traffic measurements.

        BLOCKED     The road is physically obstructed by a stopped
                    accident vehicle.  Travel time is infinity.

        UNKNOWN     Insufficient data to classify the measurement.
    """

    road_id: str
    vehicle_count: int
    average_speed: float
    road_length: float
    speed_limit: float
    lane_count: int
    occupancy: float
    travel_time: float
    congestion: str
    blocked: bool = False
    halting_count: int = 0
    measurement_status: str = UNKNOWN

    @property
    def queue_length(self) -> int:
        """Backward-compatible alias for halting_count."""
        return self.halting_count