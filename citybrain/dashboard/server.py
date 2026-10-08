"""Local GET-only evidence viewer. Does not import, launch or control CityBrain."""
import argparse
import json
import math
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import time
from urllib.parse import urlparse, parse_qs

ASSETS = Path(__file__).parent
TIMELINE = {'PLAN_ACCEPTED', 'REPLAN_ACCEPTED', 'INITIAL_EXECUTION', 'ROUTE_EXECUTION',
            'REPLAN_EXECUTION_FAILED', 'TERMINAL', 'LIFECYCLE_OBSERVATION'}


def reduce_events(events):
    """Build a display snapshot solely from observed records; never infer commands."""
    state = dict(time=None, emergency=None, ambulance=None, hospital=None, position={},
                 vehicle={}, roads={}, plan=None, previous_plan=None, decision={},
                 accepted_time=None, decision_time=None, observation_time=None,
                 initial_agents={}, execution={}, terminal=None, timeline=[], plans=[],
                 diagnostics=[], config={}, provenance={})
    for event in events:
        action = event.get('action')
        state['time'] = event.get('simulation_time')
        for field in ('emergency', 'ambulance', 'hospital'):
            if event.get(field+'_id') is not None:
                state[field] = event[field+'_id']
        context = event.get('context') or {}
        planner_state = context.get('planner_state') or {}
        if context.get('physical_position'):
            state['position'] = context['physical_position']
            # Context can be retained across records; DECISION marks an observation.
        if planner_state:
            state['roads'] = planner_state.get('roads', {})
            state['vehicle'] = planner_state.get('vehicles', {}).get(state['ambulance'], {})
            state['observation_time'] = planner_state.get('simulation_time')
        if action == 'RUNTIME_CONFIG': state['config'] = event.get('configuration', {})
        if action == 'RUN_PROVENANCE': state['provenance'] = event.get('provenance', {})
        if action in ('INITIAL_DECISION', 'DECISION'):
            state['decision'] = event.get('planner_result') or {}
            state['decision_time'] = state['time']
            if action == 'INITIAL_DECISION': state['initial_agents'] = state['decision']
        if action in ('PLAN_ACCEPTED', 'REPLAN_ACCEPTED'):
            state['previous_plan'] = state['plan']
            state['plan'] = event['accepted_plan']
            state['accepted_time'] = state['time']
            state['plans'].append(dict(time=state['time'], plan=state['plan']))
        if event.get('execution'): state['execution'] = event['execution']
        if action == 'TERMINAL':
            state['terminal'] = dict(outcome=event.get('terminal_outcome'), reason=event.get('reason'),
                                     metrics=event.get('metrics', {}))
            state['diagnostics'] = event.get('metrics', {}).get('evidence_failures', [])
        if action in TIMELINE:
            state['timeline'].append(dict(time=state['time'], action=action,
                plan_id=(event.get('accepted_plan') or event.get('execution') or {}).get('plan_id'),
                result=event.get('terminal_outcome') or (event.get('execution') or {}).get('verification')))
        if action == 'EVALUATION_TRIGGER':
            for change in event.get('events', []):
                if change.get('event_type') in ('ROAD_BLOCKED', 'ROAD_UNBLOCKED', 'CONGESTION_CHANGED', 'ROUTE_INVALIDATED'):
                    state['timeline'].append(dict(time=state['time'], action=change['event_type'],
                                                  plan_id=change.get('entity_id'), result=None))
    milestones = [e for e in state['timeline'] if e['action'] in TIMELINE]
    changes = [e for e in state['timeline'] if e['action'] not in TIMELINE][-10:]
    state['timeline'] = sorted(milestones + changes, key=lambda e: e['time'])
    return state


class EvidenceReader:
    """Incremental UTF-8 JSONL reader; partial tail records wait for a newline."""
    def __init__(self, path):
        self.path = Path(path)
        self.offset = 0
        self.identity = None
        self.pending = b''
        self.events = []
        self.errors = []
        self.modified = None

    def refresh(self):
        try:
            stat = self.path.stat()
            identity = (stat.st_dev, stat.st_ino)
            if identity != self.identity or stat.st_size < self.offset:
                self.offset = 0; self.pending = b''; self.events = []; self.errors = []
            self.identity = identity
            self.modified = stat.st_mtime
            if stat.st_size > 128 * 1024 * 1024:
                raise ValueError('Evidence exceeds viewer 128 MiB limit')
            with self.path.open('rb') as stream:
                stream.seek(self.offset)
                data = stream.read()
                self.offset = stream.tell()
            parts = (self.pending + data).split(b'\n')
            self.pending = parts.pop()
            for line in parts:
                if not line.strip(): continue
                try:
                    record = json.loads(line)
                    if not isinstance(record, dict) or not isinstance(record.get('action'), str):
                        raise ValueError('Not a runtime evidence record')
                    self.events.append(record)
                except (ValueError, UnicodeError) as error:
                    self.errors.append(str(error))
            return None
        except (OSError, ValueError) as error:
            return str(error)

    def snapshot(self, replay=False, at=None, scenario='Unspecified'):
        error = self.refresh()
        records = self.events
        if replay and at is not None:
            records = [e for e in records if float(e.get('simulation_time', 0)) <= at]
        state = reduce_events(records)
        state.update(mode='REPLAY — recorded evidence' if replay else 'LIVE — file observation',
            scenario=scenario, read_error=error, parse_errors=self.errors[-5:],
            pending_line=bool(self.pending), record_count=len(records),
            source_age_seconds=None if self.modified is None else max(0, time.time()-self.modified),
            max_time=max((e.get('simulation_time', 0) for e in self.events), default=0),
            traci_status='UNKNOWN — viewer has no TraCI connection')
        return state


def make_server(path, port=8765, replay=False, scenario='Unspecified'):
    reader = EvidenceReader(path)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlparse(self.path)
            if url.path == '/api/state':
                try:
                    query = parse_qs(url.query)
                    at = float(query['at'][0]) if replay and 'at' in query else None
                    if at is not None and not math.isfinite(at): raise ValueError('Invalid replay time')
                    payload = json.dumps(reader.snapshot(replay, at, scenario), allow_nan=False).encode()
                except (ValueError, TypeError, KeyError) as error:
                    self.send_error(400, str(error)); return
                self.respond(payload, 'application/json'); return
            assets = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'),
                      '/style.css': ('style.css', 'text/css')}
            if url.path not in assets:
                self.send_error(404); return
            filename, content_type = assets[url.path]
            self.respond((ASSETS/filename).read_bytes(), content_type)

        def respond(self, payload, content_type):
            self.send_response(200)
            self.send_header('Content-Type', content_type+'; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            try: self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError): pass

        def log_message(self, *args): pass

    return HTTPServer(('127.0.0.1', port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--events', type=Path, required=True, help='Existing or future runtime events.jsonl')
    parser.add_argument('--scenario', default='Unspecified', help='Presentation label; does not configure SUMO')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--replay', action='store_true', help='Explicitly label saved-evidence playback')
    args = parser.parse_args()
    server = make_server(args.events, args.port, args.replay, args.scenario)
    print(f'CITYBRAIN viewer: http://127.0.0.1:{server.server_port} (read-only)', flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__ == '__main__': main()
