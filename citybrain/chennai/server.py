"""Local GET-only Chennai viewer, reusing the validated dashboard reducer."""
import json
import math
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from urllib.parse import parse_qs, urlparse

from citybrain.dashboard.server import EvidenceReader
from citybrain.chennai.network import ROOT, PILOT

ASSETS = ROOT/'dashboard/cesium'


class FrameReader:
    def __init__(self, path):
        self.path = Path(path)
        self.offset = 0
        self.pending = b''
        self.frames = []
        self.error = None

    def refresh(self):
        try:
            if self.path.stat().st_size < self.offset:
                self.offset = 0
                self.pending = b''
                self.frames = []
            with self.path.open('rb') as stream:
                stream.seek(self.offset)
                data = stream.read()
                self.offset = stream.tell()
            parts = (self.pending+data).split(b'\n')
            self.pending = parts.pop()
            for line in parts:
                if not line:
                    continue
                frame = json.loads(line)
                if not isinstance(frame.get('simulation_time'), (int, float)):
                    raise ValueError('Invalid frame timestamp')
                self.frames.append(frame)
            self.error = None
        except (OSError, ValueError, KeyError) as error:
            self.error = str(error)

    def at(self, timestamp=None):
        self.refresh()
        if timestamp is None:
            return self.frames[-1] if self.frames else None
        return next((frame for frame in reversed(self.frames) if frame['simulation_time'] <= timestamp), None)


def make_server(directory, port=8770, replay=False):
    directory = Path(directory).resolve()
    reader = EvidenceReader(directory/'dashboard.jsonl')
    frames = FrameReader(directory/'telemetry.jsonl')
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlparse(self.path)
            if url.path == '/api/state':
                try:
                    query = parse_qs(url.query)
                    at = float(query['at'][0]) if replay and 'at' in query else None
                    if at is not None and (not math.isfinite(at) or at < 0):
                        raise ValueError('Invalid replay timestamp')
                    with lock:
                        state = reader.snapshot(replay=replay, at=at, scenario='CHENNAI — synthetic demand on OSM roads')
                        frame = frames.at(at)
                        state.update(chennai=frame, telemetry_error=frames.error,
                            telemetry_max_time=frames.frames[-1]['simulation_time'] if frames.frames else 0,
                            playback='REPLAY' if replay else 'LIVE_OBSERVATION')
                        state['pilot_events'] = [dict(time=e['simulation_time'], action=e['action'],
                            result=e.get('reason') or e.get('edge') or e.get('source'))
                            for e in reader.events if e['action'] in {'INCIDENT', 'ENVIRONMENT_CHANGE', 'ENVIRONMENT_RESTORED'}
                            and (at is None or e['simulation_time'] <= at)]
                    self.respond(json.dumps(state, allow_nan=False).encode(), 'application/json')
                except (ValueError, TypeError, KeyError) as error:
                    self.send_error(400, str(error))
                return
            if url.path == '/api/geography':
                self.respond((PILOT/'network/geography.json').read_bytes(), 'application/json')
                return
            assets = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'),
                      '/styles.css': ('styles.css', 'text/css')}
            if url.path in assets:
                filename, kind = assets[url.path]
                self.respond((ASSETS/filename).read_bytes(), kind)
                return
            # Optional locally installed Cesium; resolve before allowing any file read.
            if url.path.startswith('/vendor/'):
                target = (ASSETS/url.path.lstrip('/')).resolve()
                if target.is_relative_to(ASSETS/'vendor') and target.is_file():
                    self.respond(target.read_bytes(), mimetypes.guess_type(target.name)[0] or 'application/octet-stream')
                    return
            self.send_error(404)

        def respond(self, payload, content_type):
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' blob: 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://tile.openstreetmap.org; connect-src 'self' blob: https://tile.openstreetmap.org; worker-src 'self' blob:; frame-ancestors 'none'")
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *args):
            pass

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)
