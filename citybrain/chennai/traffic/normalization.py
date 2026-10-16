"""Documented provider fields only. No inferred timestamps or travel times."""
import hashlib
import json
from .models import TrafficObservation, number


def kmh_to_mps(value):
    value = number(value)
    return None if value is None else value/3.6


def identity(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()[:24]


def here_rows(payload, now, *, incidents=False):
    if not isinstance(payload,dict) or not isinstance(payload.get('results'),list):
        raise ValueError('Missing HERE results')
    if len(payload['results']) > 2000:
        raise ValueError('Too many observations')
    rows, errors = [], []
    for index, item in enumerate(payload['results']):
        try:
            location = item['location']
            links = location.get('shape',{}).get('links',[])
            # HERE explicitly allows non-consecutive shape links. Keep separate;
            # never draw a synthetic line across a split/fork.
            parts = [[(p['lng'],p['lat']) for p in link['points']] for link in links] or [[]]
            details = item['incidentDetails'] if incidents else item['currentFlow']
            segment = str(details.get('id') or location.get('olr') or 'geometry:'+identity(parts))
            for part_index,geometry in enumerate(parts):
                jam = number(details.get('jamFactor'), maximum=10)
                description = details.get('description',{})
                rows.append(TrafficObservation(
                    observation_id=identity([segment,part_index,payload.get('sourceUpdated'),details]),
                    provider='HERE',provider_segment_id=segment+':'+str(part_index),
                    road_geometry=geometry,direction='FORWARD',retrieved_at=now,source_type='HERE_LIVE',
                    current_speed=details.get('speed'),free_flow_speed=details.get('freeFlow'),
                    congestion=None if jam is None else jam/10,
                    incident_type=details.get('type') if incidents else ('ROAD_CLOSURE' if details.get('traversability')=='closed' else None),
                    incident_description=description.get('value') if isinstance(description,dict) else None,
                    observation_timestamp=payload.get('sourceUpdated'),raw_measurements=details,
                    observation_kind='INCIDENT' if incidents else 'FLOW',
                    stream_id=str(details.get('originalId') or segment)+':'+str(part_index) if incidents else None,
                    quality=('SOURCE_UPDATE_TIME; NOT INDIVIDUAL_SENSOR_TIME',)))
        except (ValueError, TypeError, KeyError, AttributeError):
            errors.append(f'INVALID_RECORD:{index}')
    return rows, errors


def tomtom_row(payload, now):
    data = payload['flowSegmentData']
    coordinates = data.get('coordinates',{}).get('coordinate',[])
    geometry = [(p['longitude'],p['latitude']) for p in coordinates]
    # The endpoint does not expose observation time. Coordinate ordering is not
    # documented as a travel bearing, so direction stays UNKNOWN until decoded
    # OpenLR or another validated directional reference becomes available.
    segment = data.get('openlr') or 'geometry:'+identity(geometry)
    return TrafficObservation(observation_id=identity([segment,data]),provider='TOMTOM',
        provider_segment_id=segment,road_geometry=geometry,direction='UNKNOWN',
        retrieved_at=now,source_type='TOMTOM_LIVE',current_speed=kmh_to_mps(data.get('currentSpeed')),
        free_flow_speed=kmh_to_mps(data.get('freeFlowSpeed')),
        current_travel_time=data.get('currentTravelTime'),free_flow_travel_time=data.get('freeFlowTravelTime'),
        incident_type='ROAD_CLOSURE' if data.get('roadClosure') is True else None,
        raw_measurements=data,quality=('MISSING_SOURCE_TIME','UNVERIFIED_GEOMETRY_DIRECTION'))
