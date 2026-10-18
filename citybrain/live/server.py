"""Loopback-only, same-origin prototype HTTP boundary with server-assigned roles."""
from collections import deque
import json
import mimetypes
import os
from pathlib import Path
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse
from citybrain.chennai.network import ROOT
from .graph import LiveError
from .service import LiveService


class Credentials:
    def __init__(self,operator=None,hospital=None,facility=None):
        self.operator=operator
        self.hospital=hospital
        self.facility=facility
        for token in (operator,hospital):
            if token is not None and (len(token)<32 or not token.isascii() or any(c.isspace() for c in token)):
                raise ValueError('Credentials must contain at least 32 non-whitespace ASCII characters')
        if operator and hospital and secrets.compare_digest(operator,hospital):
            raise ValueError('Operator and hospital credentials must be distinct')
        if hospital and not facility:
            raise ValueError('Hospital credential requires a configured facility scope')

    def role(self,header):
        if not header or not header.startswith('Bearer '):
            return None
        token=header[7:]
        if not token.isascii():
            return None
        if self.operator and secrets.compare_digest(token,self.operator):
            return 'operator'
        if self.hospital and secrets.compare_digest(token,self.hospital):
            return 'hospital'
        return None


class Limits:
    def __init__(self):
        self.rows={}
        self.lock=threading.Lock()

    def check(self,kind,limit):
        with self.lock:
            now=time.monotonic()
            queue=self.rows.setdefault(kind,deque())
            while queue and queue[0]<now-60:
                queue.popleft()
            if len(queue)>=limit:
                return False
            queue.append(now)
            return True


def make_server(service=None,credentials=None,port=8784):
    service=service or LiveService()
    credentials=credentials or Credentials()
    if credentials.facility and credentials.facility not in {h['id'] for h in service.directory}:
        raise ValueError('Configured facility is not in the directory')
    limits=Limits()
    assets=ROOT/'dashboard/live'
    cesium=ROOT/'dashboard/cesium/vendor'

    class Handler(BaseHTTPRequestHandler):
        protocol_version='HTTP/1.0'

        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def reply(self,value,status=200,kind='application/json'):
            payload=json.dumps(value,allow_nan=False).encode() if kind=='application/json' else value
            self.send_response(status)
            self.send_header('Content-Type',kind)
            self.send_header('Content-Length',str(len(payload)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Permissions-Policy','camera=(), microphone=(), geolocation=(self)')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' blob: 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://tile.openstreetmap.org; connect-src 'self' blob: https://tile.openstreetmap.org; worker-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (BrokenPipeError,ConnectionResetError):
                pass

        def boundary(self):
            host=self.headers.get('Host','')
            allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
            if host not in allowed:
                raise LiveError('INVALID_HOST')
            origin=self.headers.get('Origin')
            if origin and origin!=f'http://{host}':
                raise LiveError('INVALID_ORIGIN')
            return credentials.role(self.headers.get('Authorization'))

        def do_GET(self):
            try:
                role=self.boundary()
                path=urlparse(self.path).path
                if path=='/api/live/session':
                    if not role:
                        return self.reply(dict(error='AUTHENTICATION_REQUIRED'),401)
                    return self.reply(dict(role=role,facility=credentials.facility if role=='hospital' else None))
                if path=='/api/live/state':
                    if self.headers.get('Authorization') and not role:
                        return self.reply(dict(error='AUTHENTICATION_REQUIRED'),401)
                    result=service.state(operator=role=='operator')
                    if role!='operator':
                        for hospital in result['hospitals']:
                            if hospital['status'] and (role!='hospital' or hospital['id']!=credentials.facility):
                                hospital['status']={k:v for k,v in hospital['status'].items() if k not in {'notes','operator'}}
                    return self.reply(result)
                if path=='/api/live/geography':
                    return self.reply(service.graph.geography())
                static={'/':'index.html','/app.js':'app.js','/styles.css':'styles.css'}
                target=assets/static[path] if path in static else None
                if path.startswith('/vendor/'):
                    target=(cesium/path.removeprefix('/vendor/')).resolve()
                    if not target.is_relative_to(cesium.resolve()):
                        target=None
                if target and target.is_file():
                    return self.reply(target.read_bytes(),kind=mimetypes.guess_type(target.name)[0] or 'application/octet-stream')
                self.reply(dict(error='NOT_FOUND'),404)
            except LiveError as error:
                self.reply(dict(error=error.code,detail=error.detail),403)
            except Exception:
                self.reply(dict(error='INTERNAL_ERROR'),500)

        def do_POST(self):
            try:
                role=self.boundary()
                path=urlparse(self.path).path
                if not limits.check('writes',120):
                    return self.reply(dict(error='RATE_LIMITED'),429)
                if path!='/api/live/incidents' and not role:
                    if not limits.check('auth',10):
                        return self.reply(dict(error='RATE_LIMITED'),429)
                    return self.reply(dict(error='AUTHENTICATION_REQUIRED'),401)
                if path=='/api/live/incidents' and not limits.check('public_reports',5):
                    return self.reply(dict(error='RATE_LIMITED'),429)
                if self.headers.get('Content-Type','').split(';')[0]!='application/json':
                    return self.reply(dict(error='JSON_REQUIRED'),415)
                try:
                    size=int(self.headers.get('Content-Length','0'))
                except ValueError:
                    size=0
                if not 1<=size<=16384:
                    return self.reply(dict(error='BODY_SIZE_LIMIT'),413)
                def invalid_constant(_):
                    raise ValueError('Nonfinite JSON')
                body=json.loads(self.rfile.read(size),parse_constant=invalid_constant)
                if not isinstance(body,dict):
                    raise LiveError('OBJECT_REQUIRED')
                if path=='/api/live/incidents':
                    return self.reply(service.submit(body),201)
                if path=='/api/live/hospital':
                    key=body.get('hospital_id')
                    if role!='hospital' or key!=credentials.facility:
                        return self.reply(dict(error='FACILITY_AUTHORIZATION_REQUIRED'),403)
                    return self.reply(service.hospital_update(key,body,'facility:'+key))
                if role!='operator':
                    return self.reply(dict(error='OPERATOR_AUTHORIZATION_REQUIRED'),403)
                if path=='/api/live/verify':
                    return self.reply(service.verify(body.get('id'),body.get('status')))
                if path=='/api/live/position':
                    return self.reply(service.position(body))
                if path=='/api/live/recommend':
                    return self.reply(service.recommend(body))
                if path=='/api/live/transition':
                    return self.reply(service.transition(body.get('status')))
                if path=='/api/live/delete':
                    key=body.get('id')
                    service.verify(key,'RESOLVED') if service.store.get('incidents',key) and service.store.get('incidents',key)['status']=='VERIFIED_FOR_TESTING' else None
                    service.store.delete('incidents',key)
                    service.audit('INCIDENT_DELETED',key,'operator')
                    return self.reply(dict(deleted=True))
                if path=='/api/live/traffic-test' and service.traffic:
                    result=service.traffic.inject(body)
                    service.reassess('SYNTHETIC_TRAFFIC_CHANGED')
                    return self.reply(result)
                self.reply(dict(error='NOT_FOUND'),404)
            except LiveError as error:
                self.reply(dict(error=error.code,detail=error.detail),400)
            except (ValueError,TypeError,KeyError):
                self.reply(dict(error='INVALID_REQUEST'),400)
            except Exception:
                # Never return adapter exceptions, credentials or request bodies.
                self.reply(dict(error='INTERNAL_ERROR'),500)

        def log_message(self,*args):
            pass

    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.daemon_threads=True
    return server
