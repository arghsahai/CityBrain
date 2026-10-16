"""Source time, never retrieval time, determines measurement age."""
from dataclasses import dataclass
import math
from .models import timestamp


@dataclass(frozen=True)
class FreshnessPolicy:
    fresh_seconds: float = 120
    expired_seconds: float = 600
    future_tolerance: float = 5

    def __post_init__(self):
        if any(isinstance(v,bool) or not math.isfinite(v) or v < 0 for v in (self.fresh_seconds,self.expired_seconds,self.future_tolerance)) or self.expired_seconds < self.fresh_seconds:
            raise ValueError('Invalid freshness thresholds')

    def classify(self, observed, now):
        if observed is None:
            return 'UNKNOWN', None, 'MISSING_SOURCE_TIME'
        age = (timestamp(now)-timestamp(observed)).total_seconds()
        if age < -self.future_tolerance:
            return 'UNKNOWN', age, 'SOURCE_CLOCK_AHEAD'
        return ('FRESH' if age <= self.fresh_seconds else 'STALE' if age <= self.expired_seconds else 'EXPIRED'), age, None
