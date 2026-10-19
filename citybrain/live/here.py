"""V4 HERE v7 session: explicit authorization, separate bounded transactions.

Mock transport and local HERE fixtures are always REPLAY, never HERE_LIVE.
This module alone owns the optional network activation boundary; no caller
can activate it with a key or a browser request alone.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone, timedelta
import json
import math
import os
from pathlib import Path
import threading

from citybrain.chennai.traffic.here_provider import HERETrafficProvider
from citybrain.chennai.traffic.models import timestamp
from citybrain.chennai.traffic.provider import FetchResult, bounds, http_json
from .graph import BOUNDS, LiveError
from .traffic import OfflineTraffic
from citybrain.chennai.traffic.service import TrafficService
from citybrain.chennai.traffic.matching import RoadMatcher

ENDPOINTS = {kind:'https://data.traffic.hereapi.com/v7/'+kind for kind in ('flow','incidents')}


def readiness():
    """No network, key value, authenticated URL or implicit activation."""
    return dict(provider='HERE',status='CONFIGURED_NOT_VERIFIED' if os.environ.get('HERE_API_KEY') else 'NOT_CONFIGURED',
                requests_enabled=False,live_verified=False,
                required=['Explicit authorization','Licensed routing/tracking and retention use',
                          'Approved pilot bounds','Per-endpoint and total transaction budget','HERE_API_KEY'])


class BudgetStop(Exception):
    pass


class HEREQuerySession:
    name='HERE'

    def __init__(self, *, area=None, authorized=False, licensed=False, max_requests=0,
                 flow_limit=None, incident_limit=None, incidents=True, poll_seconds=60,
                 session_seconds=900, transport=None, fixture=None, clock=None):
        if any(type(value) is not bool for value in (authorized,licensed,incidents)):
            raise ValueError('Authorization and endpoint switches require explicit booleans')
        self.clock=clock or (lambda:datetime.now(timezone.utc))
        self.bounds=bounds(area if area is not None else BOUNDS)
        if not (BOUNDS[0]<=self.bounds[0]<self.bounds[2]<=BOUNDS[2] and
                BOUNDS[1]<=self.bounds[1]<self.bounds[3]<=BOUNDS[3]):
            raise ValueError('HERE query area must remain inside the retained routing pilot')
        if type(max_requests) is not int or not 0<=max_requests<=100:
            raise ValueError('Total transaction budget must be 0..100')
        self.limits={'flow':max_requests if flow_limit is None else flow_limit,
                     'incidents':max_requests if incident_limit is None else incident_limit}
        if any(type(v) is not int or not 0<=v<=max_requests for v in self.limits.values()):
            raise ValueError('Endpoint limits must be within the total transaction budget')
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (poll_seconds,session_seconds)) or not 60<=poll_seconds<=3600 or not 1<=session_seconds<=900:
            raise ValueError('Poll interval must be 60..3600 s; session duration 1..900 s')
        if authorized and (not licensed or area is None or max_requests==0):
            raise ValueError('Authorization requires licensed use, explicit area and nonzero budget')
        if fixture is not None and transport is not None:
            raise ValueError('Choose a fixture or mock transport, not both')
        self.fixture=None
        if fixture is not None:
            path=Path(fixture)
            if path.stat().st_size>2*1024*1024:
                raise ValueError('HERE fixture exceeds 2 MiB')
            self.fixture=json.loads(path.read_text())
            if not isinstance(self.fixture,dict) or self.fixture.get('provenance') not in {'MOCKED_HERE','RECORDED_HERE'}:
                raise ValueError('HERE fixture requires declared MOCKED_HERE or RECORDED_HERE provenance')
        self.mocked=fixture is not None or transport is not None
        self.enabled=self.mocked or (authorized and licensed and bool(os.environ.get('HERE_API_KEY')))
        self.max_requests=max_requests
        self.poll_seconds=poll_seconds
        self.session_seconds=session_seconds
        self.started=self.clock()
        self.next_poll=self.started
        self.requests={'flow':0,'incidents':0}
        self.real_requests={'flow':0,'incidents':0}
        self._lock=threading.RLock()
        self._fetch_lock=threading.Lock()
        self._transport=transport or http_json
        self.stop_reason=None
        self._closed=False
        self._endpoint_status={k:'NOT_REQUESTED' for k in ENDPOINTS}
        self._provider=HERETrafficProvider(study_bounds=self.bounds,incidents=False,
            api_key='OFFLINE_NO_CREDENTIAL' if self.mocked else None,
            authorized=self.enabled,transport=self._transaction)
        self.incidents=incidents
        self.last_result='REPLAY_READY' if self.mocked else readiness()['status']

    @property
    def status(self):
        return self.last_result

    def _transaction(self,endpoint,params,timeout):
        kind=next((kind for kind,url in ENDPOINTS.items() if endpoint==url),None)
        with self._lock:
            if kind is None or not self.enabled or self._closed:
                raise BudgetStop('REQUESTS_DISABLED')
            if sum(self.requests.values())>=self.max_requests or self.requests[kind]>=self.limits[kind]:
                raise BudgetStop('BUDGET_EXHAUSTED')
            if (self.clock()-self.started).total_seconds()>self.session_seconds:
                raise BudgetStop('SESSION_EXPIRED')
            # Count before I/O: unsuccessful attempts also consume budget. No retries here.
            self.requests[kind]+=1
            self.real_requests[kind]+=int(not self.mocked)
        if self.fixture is not None:
            return deepcopy(self.fixture[kind])
        return self._transport(endpoint,params,timeout)

    def fetch(self,now):
        with self._fetch_lock:
            if not self.enabled or self._closed:
                return FetchResult(status='REQUESTS_DISABLED' if self._closed else self.last_result)
            if now<self.next_poll:
                return FetchResult(status='NOT_DUE',retry_after=(self.next_poll-now).total_seconds())
            self.next_poll=now+timedelta(seconds=self.poll_seconds)
            rows,errors,delays=[],[],[]
            states=[]
            for kind in ('flow','incidents') if self.incidents else ('flow',):
                # Reuse the established request, timeout, normalization and error boundary.
                self._provider.incidents=False
                try:
                    if kind=='flow':
                        result=self._provider.fetch(now)
                    else:
                        from citybrain.chennai.traffic.normalization import here_rows
                        # HTTPProvider.fetch supplies identical sanitization for incidents.
                        class IncidentProvider(HERETrafficProvider):
                            def request(inner,current):
                                params={'in':'bbox:'+','.join(map(str,self.bounds)),
                                        'locationReferencing':'shape','apiKey':inner._key}
                                observations,invalid=here_rows(inner.transport(ENDPOINTS['incidents'],params,inner.timeout),current,incidents=True)
                                return FetchResult(observations,'FETCHED',invalid)
                        result=IncidentProvider(api_key=self._provider._key,authorized=True,transport=self._transaction).fetch(now)
                except BudgetStop as stop:
                    self.stop_reason=str(stop)
                    result=FetchResult(status=self.stop_reason,errors=[self.stop_reason])
                except Exception:
                    result=FetchResult(status='PROVIDER_UNAVAILABLE',errors=['PROVIDER_UNAVAILABLE'],retry_after=60)
                states.append(result.status);self._endpoint_status[kind]=result.status
                delays.append(result.retry_after)
                errors.extend(kind.upper()+':'+error for error in result.errors)
                for row in result.observations:
                    raw=row.raw_measurements
                    incident=row.incident_type
                    if row.observation_kind=='INCIDENT':
                        if raw.get('roadClosed') is False or raw.get('status') in {'inactive','completed','cancelled'}:
                            incident='ROAD_REOPENED'
                        elif raw.get('roadClosed') is True or raw.get('type')=='roadClosure' and raw.get('status')=='active':
                            incident='ROAD_CLOSURE'
                    quality=list(row.quality)
                    if not all(self.bounds[0]<=p[0]<=self.bounds[2] and self.bounds[1]<=p[1]<=self.bounds[3] for p in row.road_geometry):
                        quality.append('OUTSIDE_QUERY_AREA')
                    if row.observation_kind=='FLOW':
                        if raw.get('traversability') in {'closed','reversibleNotRoutable'} or raw.get('jamFactor')==10:
                            incident='ROAD_CLOSURE'
                        confidence=raw.get('confidence')
                        if incident!='ROAD_CLOSURE' and (isinstance(confidence,bool) or not isinstance(confidence,(float,int)) or not .7<float(confidence)<=1):
                            quality.append('NON_REALTIME_OR_UNKNOWN_CONFIDENCE')
                    if raw.get('subSegments'):
                        quality.append('SUBSEGMENT_COST_NOT_SUPPORTED')
                    if row.observation_kind=='INCIDENT' and raw.get('startTime'):
                        try:
                            if timestamp(raw['startTime'])>now:
                                quality.append('INCIDENT_NOT_YET_ACTIVE')
                        except (ValueError,TypeError):
                            quality.append('INVALID_INCIDENT_END_TIME')
                    if row.observation_kind=='INCIDENT' and raw.get('endTime'):
                        try:
                            if timestamp(raw['endTime'])<=now:
                                incident='ROAD_REOPENED'
                        except (ValueError,TypeError):
                            quality.append('INVALID_INCIDENT_END_TIME')
                    rows.append(replace(row,incident_type=incident,quality=tuple(quality),
                        source_type='REPLAY' if self.mocked else 'HERE_LIVE',
                        recording_provenance=self.fixture['provenance'] if self.fixture is not None else 'MOCKED_HERE' if self.mocked else None))
            # A failed endpoint remains visible even if the other endpoint succeeded.
            bad=next((s for s in states if s!='FETCHED' and s!='COVERAGE_UNVERIFIED_OR_INSUFFICIENT'),None)
            self.last_result=bad or ('REPLAY' if self.mocked else 'FETCHED')
            delay=max([self.poll_seconds,*delays])
            self.next_poll=now+timedelta(seconds=delay)
            return FetchResult(rows,self.last_result,errors[:20],delay)

    def accounting(self):
        with self._lock:
            return dict(mode='REPLAY' if self.mocked else 'AUTHORIZED_NETWORK' if self.enabled else 'DISABLED',
                attempted=dict(self.requests),real_requests=dict(self.real_requests),
                total_limit=self.max_requests,endpoint_limits=dict(self.limits),
                remaining=max(0,self.max_requests-sum(self.requests.values())),
                endpoint_status=dict(self._endpoint_status),stop_reason=self.stop_reason,
                area=self.bounds,poll_seconds=self.poll_seconds,session_seconds=self.session_seconds)

    def close(self):
        with self._lock:
            self._closed=True


class HERETraffic(OfflineTraffic):
    """Same eligible-cost builder as offline V4; only ingestion/provenance differ."""
    def __init__(self,graph,clock=None,on_update=None,**options):
        self.graph=graph
        self.clock=clock or (lambda:datetime.now(timezone.utc))
        self.recording=False
        self.last_poll=None
        self.queue=HEREQuerySession(clock=self.clock,**options)
        self.on_update=on_update
        self._wake=threading.Event()
        self._worker=None
        self.callback_failures=0
        self.service=TrafficService(self.queue,RoadMatcher(graph.net),clock=self.clock,poll_seconds=self.queue.poll_seconds,max_records=256)

    def start(self):
        # Background I/O only. Snapshots and operator requests never initiate HTTP.
        if self._worker is not None:
            return
        def loop():
            while not self._wake.is_set():
                delay=self.service.poll_once()
                if not self._wake.is_set() and self.on_update:
                    try:
                        self.on_update()
                    except Exception:
                        self.callback_failures+=1  # Sanitized count, never exception text.
                self._wake.wait(delay)
        self._worker=threading.Thread(target=loop,name='citybrain-live-here',daemon=True)
        self._worker.start()

    def inject(self,body):
        raise LiveError('SYNTHETIC_INJECTION_DISABLED_DURING_HERE_SESSION')

    def source_label(self,row):
        # Only the non-injected gated transport may retain HERE_LIVE.
        return 'REPLAY' if self.queue.mocked else 'HERE_LIVE'

    def snapshot(self):
        result=super().snapshot()
        raw=self.service.snapshot(self.clock())
        verified=not self.queue.mocked and raw['status']=='FETCHED' and any(r['eligible_for_routing'] for r in result['observations'])
        for row in result['observations']:
            row['live_verified']=verified and row['eligible_for_routing']
        result.update(provider='HERE',last_update=raw['last_update'],last_attempt=raw['last_attempt'],
            accounting=self.queue.accounting(),live_verified=verified,reassessment_callback_failures=self.callback_failures,
            providers={'HERE':'LIVE_VERIFIED' if verified else raw['status']},
            provider_access='AUTHORIZED_BOUNDED_SESSION' if self.queue.enabled and not self.queue.mocked else 'OFFLINE_ONLY' if self.queue.mocked else 'DISABLED',
            offline_test_enabled=False)
        # A stale/cached row retains its source provenance, but not a current live status.
        result['source']='HERE_LIVE' if verified else 'REPLAY' if self.queue.mocked and result['observations'] else 'UNAVAILABLE'
        return result

    def close(self):
        self._wake.set()
        self.service.stop()
        self.queue.close()


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description='HERE readiness only; never sends a request')
    parser.add_argument('--status',action='store_true')
    parser.parse_args()
    print(json.dumps(readiness(),indent=2))
