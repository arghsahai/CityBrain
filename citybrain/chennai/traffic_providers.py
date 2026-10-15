"""Optional external observations. They cannot overwrite SUMO planner state.

Live adapters are deliberately disabled pending credentials, coverage and terms
verification. Replay records require explicit, geometrically checked edge maps.
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import math
from typing import Protocol


@dataclass(frozen=True)
class TrafficObservation:
    segment_id: str
    longitude: float
    latitude: float
    speed_mps: float
    free_flow_speed_mps: float
    travel_time_s: float
    congestion: float
    incident: str
    provider_timestamp: str
    source: str = 'REPLAY'

    def __post_init__(self):
        for key in ('longitude', 'latitude', 'speed_mps', 'free_flow_speed_mps', 'travel_time_s', 'congestion'):
            if not math.isfinite(getattr(self, key)):
                raise ValueError('Non-finite observation')
        if not (-180 <= self.longitude <= 180 and -90 <= self.latitude <= 90):
            raise ValueError('Invalid coordinates')
        if min(self.speed_mps, self.free_flow_speed_mps, self.travel_time_s) < 0 or not 0 <= self.congestion <= 1:
            raise ValueError('Invalid traffic values')
        if datetime.fromisoformat(self.provider_timestamp).tzinfo is None:
            raise ValueError('Timestamp must include timezone')
        if self.source != 'REPLAY':
            raise ValueError('Offline fixture must be labeled REPLAY')


class TrafficProvider(Protocol):
    def observations(self, now: datetime) -> dict: ...


class ReplayProvider:
    def __init__(self, path, net, segment_mapping):
        self.records = [TrafficObservation(**row) for row in json.loads(path.read_text())]
        self.net, self.mapping = net, dict(segment_mapping)

    def observations(self, now):
        rows = []
        for record in self.records:
            timestamp = datetime.fromisoformat(record.provider_timestamp)
            if timestamp > now:
                continue
            edge_id = self.mapping.get(record.segment_id)
            matched = False
            distance = None
            if edge_id and self.net.hasEdge(edge_id):
                x, y = self.net.convertLonLat2XY(record.longitude, record.latitude)
                from sumolib.geomhelper import distancePointToPolygon
                distance = distancePointToPolygon((x, y), self.net.getEdge(edge_id).getShape())
                matched = distance <= 30
            age = (now-timestamp).total_seconds()
            rows.append(dict(**asdict(record), sumo_edge=edge_id if matched else None,
                match_validated=matched, match_distance_m=distance, age_seconds=age,
                fresh=age <= 120, applied_to_sumo=False))
        return dict(source='REPLAY', observations=rows, status='Read-only offline fixture')


class HEREProvider:
    def observations(self, now):
        return dict(source='UNAVAILABLE', provider='HERE', observations=[],
            reason='Live adapter not implemented; credentials, coverage and licensing unverified')


class TomTomProvider:
    def observations(self, now):
        return dict(source='UNAVAILABLE', provider='TomTom', observations=[],
            reason='Live adapter not implemented; credentials, coverage and licensing unverified')
