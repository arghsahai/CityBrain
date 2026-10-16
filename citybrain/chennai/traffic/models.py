"""Provider-neutral advisory measurements: SI units, WGS84, UTC; never planner input."""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import math
import json

SOURCES = {'HERE_LIVE', 'TOMTOM_LIVE', 'REPLAY', 'SYNTHETIC_SAMPLE'}


def timestamp(value):
    if value is None:
        return None
    value = datetime.fromisoformat(value.replace('Z', '+00:00')) if isinstance(value, str) else value
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('Timestamp requires timezone')
    return value.astimezone(timezone.utc)


def number(value, *, maximum=None):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
        raise ValueError('Invalid nonnegative measurement')
    if maximum is not None and value > maximum:
        raise ValueError('Measurement outside range')
    return float(value)


@dataclass(frozen=True)
class TrafficObservation:
    observation_id: str
    provider: str
    provider_segment_id: str | None
    road_geometry: tuple
    direction: str
    retrieved_at: datetime
    source_type: str
    current_speed: float | None = None
    free_flow_speed: float | None = None
    current_travel_time: float | None = None
    free_flow_travel_time: float | None = None
    congestion: float | None = None
    incident_type: str | None = None
    incident_description: str | None = None
    observation_timestamp: datetime | None = None
    freshness_status: str = 'UNKNOWN'
    matching_status: str = 'INSUFFICIENT_DATA'
    matched_sumo_edges: tuple = ()
    matching_confidence: float | None = None
    matching_coverage: float | None = None
    match_reason: str = 'Not evaluated'
    raw_measurements: dict = field(default_factory=dict)
    quality: tuple = ()
    recording_provenance: str | None = None

    def __post_init__(self):
        if not isinstance(self.observation_id,str) or not isinstance(self.provider,str) or not self.observation_id or not self.provider or self.source_type not in SOURCES:
            raise ValueError('Invalid observation identity/source')
        for key in ('provider_segment_id','incident_type','incident_description'):
            value = getattr(self,key)
            if value is not None and (not isinstance(value,str) or len(value)>4096):
                raise ValueError('Invalid textual measurement')
        if not isinstance(self.raw_measurements,dict):
            raise ValueError('Raw measurements must be an object')
        if len(json.dumps(self.raw_measurements,allow_nan=False)) > 65536:
            raise ValueError('Raw measurement exceeds record budget')
        if self.direction not in {'FORWARD', 'UNKNOWN'}:
            raise ValueError('Direction must be FORWARD along geometry or UNKNOWN')
        for key in ('current_speed', 'free_flow_speed', 'current_travel_time', 'free_flow_travel_time', 'congestion', 'matching_confidence', 'matching_coverage'):
            object.__setattr__(self, key, number(getattr(self, key), maximum=1 if key in {'congestion','matching_confidence','matching_coverage'} else None))
        for key in ('observation_timestamp', 'retrieved_at'):
            object.__setattr__(self, key, timestamp(getattr(self, key)))
        if self.retrieved_at is None:
            raise ValueError('Retrieval time required')
        geometry = tuple(tuple(p) for p in self.road_geometry)
        if len(geometry) > 4096:
            raise ValueError('Geometry too large')
        for point in geometry:
            if len(point) != 2 or any(isinstance(v, bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in point):
                raise ValueError('Invalid geometry')
            if not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
                raise ValueError('Coordinates outside WGS84')
        for a,b in zip(geometry,geometry[1:]):
            distance = math.hypot((a[0]-b[0])*111320*math.cos(math.radians(a[1])), (a[1]-b[1])*111320)
            if distance > 2000:
                raise ValueError('Discontinuous geometry; split into observations')
        object.__setattr__(self, 'road_geometry', geometry)

    def to_dict(self):
        result = asdict(self)
        for key in ('retrieved_at', 'observation_timestamp'):
            result[key] = result[key].isoformat() if result[key] else None
        result['applied_to_sumo'] = False
        return result
