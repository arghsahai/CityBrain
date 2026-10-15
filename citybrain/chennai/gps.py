"""Consent-gated recorded/synthetic GPS input; no live tracking endpoint."""
from dataclasses import dataclass, asdict
from datetime import datetime
import math


@dataclass(frozen=True)
class GPSObservation:
    vehicle_id: str
    longitude: float
    latitude: float
    timestamp: str
    speed_mps: float
    accuracy_m: float
    consent: bool
    session_active: bool
    source: str = 'GPS_REPLAY'

    def __post_init__(self):
        if self.consent is not True or self.session_active is not True:
            raise ValueError('Explicit active consent required')
        if self.source != 'GPS_REPLAY':
            raise ValueError('Only recorded/synthetic replay is supported')
        if not all(math.isfinite(v) for v in (self.longitude, self.latitude, self.speed_mps, self.accuracy_m)):
            raise ValueError('Non-finite GPS observation')
        if not (-180 <= self.longitude <= 180 and -90 <= self.latitude <= 90) or min(self.speed_mps, self.accuracy_m) < 0:
            raise ValueError('Invalid GPS observation')
        if datetime.fromisoformat(self.timestamp).tzinfo is None:
            raise ValueError('Timestamp must include timezone')


def replay(records, now, retention_seconds=120):
    if not math.isfinite(retention_seconds) or retention_seconds <= 0:
        raise ValueError('Retention must be positive and finite')
    observations = [GPSObservation(**record) for record in records]
    return [asdict(obs) for obs in observations
            if 0 <= (now-datetime.fromisoformat(obs.timestamp)).total_seconds() <= retention_seconds]
