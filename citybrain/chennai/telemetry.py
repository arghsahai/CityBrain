"""Failure-isolated, file-only telemetry bridge; never controls SUMO."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from citybrain.integration.evidence import snapshot


def compact_event(record):
    """Existing dashboard reducer consumes unchanged fields, with less context."""
    def project(value):
        if isinstance(value, dict):
            result = {k: project(v) for k, v in value.items() if k != 'components'}
            for key in ('active_plan', 'current_plan', 'proposed_plan', 'last_accepted_plan'):
                if isinstance(result.get(key), dict):
                    result[key].pop('recommendations', None)
            return result
        if isinstance(value, list):
            return [project(v) for v in value if not (isinstance(v, dict) and
                    v.get('congestion') == 'NO_TRAFFIC' and 'recommendation' in v)]
        return value
    record = project(record)
    if record.get('action') == 'STABILITY_DECISION':
        # The immediately preceding DECISION already supplies this observation.
        # Keep the effective result, scores and guard evidence without duplicating
        # every background vehicle in the compact presentation stream.
        record.pop('context', None)
        record.pop('active_plan', None)
    state = record.get('context', {}).get('planner_state', {})
    if state:
        relevant = {edge for path in state.get('routes', {}).values() for edge in path}
        # The pilot's all-active-road observations arrive in telemetry.jsonl.
        # Candidate component details and full planner inputs remain in raw evidence.
        state['roads'] = {}
        state.pop('routes', None)
        record['context'].pop('candidate_routes', None)
    return record


class DashboardWriter:
    def __init__(self, writer, dashboard_path):
        self.writer = writer
        self.dashboard_path = dashboard_path
        self.failures = 0

    def append(self, record):
        self.writer.append(record)
        try:
            with self.dashboard_path.open('a') as stream:
                stream.write(json.dumps(compact_event(record), allow_nan=False)+'\n')
        except Exception:
            self.failures += 1

    def summary(self, value):
        self.writer.summary(value)


def observe(runtime, hospitals, external=None, gps=None):
    frame = runtime.core.traci.geographic_observations()
    frame.update(observed_at_utc=datetime.now(timezone.utc).isoformat(), hospitals=hospitals,
        ambulance_id=runtime.ambulance_id, terminal_outcome=runtime.terminal_outcome,
        incident=dict(longitude=80.170, latitude=12.829, source='SIMULATED_INCIDENT'),
        roads={key: dict(speed=value.average_speed, speed_limit=value.speed_limit,
            vehicles=value.vehicle_count, queue=value.halting_count, congestion=value.congestion,
            blocked=value.blocked, source='SUMO_SIMULATED', simulation_time=runtime.now)
            for key, value in runtime.core.city_state.roads.items() if value.vehicle_count or value.blocked},
        external=external or dict(source='UNAVAILABLE', reason='No live API credentials configured'),
        gps=gps or [], health=dict(traci='Observed on Core connection'))
    return snapshot(frame)


def emit(runtime, hospitals, path, external=None, gps=None):
    try:
        frame = observe(runtime, hospitals, external, gps)
        payload = json.dumps(frame, allow_nan=False)
        with path.open('a') as stream:
            stream.write(payload+'\n')
        return True
    except Exception:
        return False
