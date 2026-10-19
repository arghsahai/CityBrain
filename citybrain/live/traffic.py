"""Offline-only traffic adapter for the V4 graph. No network transport exists.

Reuse V2 normalization/matching/freshness/ordering/quarantine. Credentials merely
report readiness; even configured keys cannot enable requests in this module.
"""
from datetime import datetime,timezone,timedelta
import math
import os
import secrets
from citybrain.chennai.traffic.models import TrafficObservation
from citybrain.chennai.traffic.provider import FetchResult
from citybrain.chennai.traffic.service import TrafficService
from citybrain.chennai.traffic.matching import RoadMatcher,segments,overlap_interval
from .graph import LiveError


class OfflineQueue:
    name='REPLAY'
    status='UNAVAILABLE'
    def __init__(self):
        self.result=FetchResult(status='UNAVAILABLE')
    def fetch(self,now):
        result=self.result
        self.result=FetchResult(status=result.status)
        return result


def edge_coverage(graph,eid,observation):
    """Provider coverage alone cannot establish full-road cost coverage.

    Measure finite longitudinal coverage in the opposite direction too: the
    actual edge must lie inside the finite provider strips. Parallel direction
    and the existing conservative match are prerequisites.
    """
    provider=list(segments([graph.net.convertLonLat2XY(*p) for p in observation['road_geometry']]))
    total=covered=0.0
    for a,b,length,_,direction in graph.edges[eid]['parts']:
        intervals=[]
        for c,d,other_length,_,other_direction in provider:
            if sum(x*y for x,y in zip(direction,other_direction))<math.cos(math.radians(35)):
                continue
            interval=overlap_interval(a,b,c,other_length,other_direction,15)
            if interval:
                intervals.append(interval)
        end=0
        for lo,hi in sorted(intervals):
            covered+=max(0,hi-max(lo,end))*length
            end=max(end,hi)
        total+=length
    return covered/total if total else 0


class OfflineTraffic:
    def __init__(self,graph,clock=None,recording=None):
        self.graph=graph
        self.clock=clock or (lambda:datetime.now(timezone.utc))
        self.recording=recording is not None
        if recording:
            from citybrain.chennai.traffic.replay_provider import ReplayTrafficProvider
            self.queue=ReplayTrafficProvider(recording)
        else:
            self.queue=OfflineQueue()
        self.last_poll=None
        self.service=TrafficService(self.queue,RoadMatcher(graph.net),clock=self.clock,max_records=256)

    def inject(self,body):
        if self.recording:
            raise LiveError('SYNTHETIC_INJECTION_DISABLED_DURING_RECORDING')
        eid=body.get('edge')
        condition=body.get('condition')
        if condition not in {'FLOW','CLOSURE','REOPEN','FUTURE','OUTAGE'}:
            raise LiveError('INVALID_SYNTHETIC_CONDITION')
        if condition=='OUTAGE':
            self.queue.result=FetchResult(status='PROVIDER_UNAVAILABLE',errors=['SYNTHETIC_OUTAGE'])
        else:
            if eid not in self.graph.edges:
                raise LiveError('UNKNOWN_PILOT_EDGE')
            now=self.clock()
            kind='INCIDENT' if condition in {'CLOSURE','REOPEN'} else 'FLOW'
            row=TrafficObservation(observation_id=secrets.token_hex(8),provider='OFFLINE_TEST',
                provider_segment_id=eid,stream_id='synthetic:'+kind+':'+eid,
                observation_kind=kind,road_geometry=tuple(map(tuple,self.graph.edges[eid]['coordinates'])),
                direction='FORWARD',retrieved_at=now,source_type='SYNTHETIC_SAMPLE',
                observation_timestamp=now+timedelta(days=365) if condition=='FUTURE' else now,
                current_speed=2 if condition in {'FLOW','FUTURE'} else None,
                incident_type='ROAD_CLOSURE' if condition=='CLOSURE' else 'ROAD_REOPENED' if condition=='REOPEN' else None,
                recording_provenance='SYNTHETIC_SAMPLE')
            self.queue.result=FetchResult([row],status='REPLAY')
        self.service.poll_once()
        return self.snapshot()

    def source_label(self,row):
        return 'SYNTHETIC_TEST' if row['source_type']=='SYNTHETIC_SAMPLE' else 'RECORDED_PROVIDER_REPLAY'

    def snapshot(self):
        if self.recording and (self.last_poll is None or (self.clock()-self.last_poll).total_seconds()>=1):
            self.service.poll_once()
            self.last_poll=self.clock()
        snapshot=self.service.snapshot(self.clock())
        costs={}
        # Oldest first makes the newest eligible flow win deterministically.
        rows=sorted(snapshot['observations'],key=lambda r:(r['observation_timestamp'] or '',r['observation_id']))
        for row in rows:
            row['source_type']=self.source_label(row)
            row['live_verified']=False
            eligible=row['matching_status']=='MATCHED' and row['freshness_status']=='FRESH' and row['direction']=='FORWARD'
            row['eligible_for_routing']=False
            row['edge_coverages']={}
            row['validation_status']='INELIGIBLE'
            if any(q in row.get('quality',[]) for q in ('SUBSEGMENT_COST_NOT_SUPPORTED','INVALID_INCIDENT_END_TIME','NON_REALTIME_OR_UNKNOWN_CONFIDENCE','OUTSIDE_QUERY_AREA','INCIDENT_NOT_YET_ACTIVE')):
                eligible=False
            if not eligible:
                continue
            for eid in row['matched_sumo_edges']:
                if eid not in self.graph.edges:
                    continue
                coverage=edge_coverage(self.graph,eid,row)
                row['edge_coverages'][eid]=coverage
                if coverage < .95:
                    continue  # Partial measurements stay visible, not full-road costs.
                if row['incident_type']=='ROAD_CLOSURE':
                    costs.setdefault(eid,{}).update(blocked=True,reason='VALIDATED_CLOSURE',source=row['source_type'],freshness='FRESH',source_time=row['observation_timestamp'])
                    row['eligible_for_routing']=True
                if row['observation_kind']=='INCIDENT':
                    continue  # Reopening replaces its stream but invents no speed.
                speed=row['current_speed']
                if speed is None and row['current_travel_time'] and row['current_travel_time']>0:
                    points=[self.graph.net.convertLonLat2XY(*p) for p in row['road_geometry']]
                    speed=sum(p[2] for p in segments(points))/row['current_travel_time']
                if speed is not None and speed==0:
                    costs.setdefault(eid,{}).update(blocked=True,reason='ZERO_OBSERVED_SPEED')
                    row['eligible_for_routing']=True
                if speed is not None and speed>70:
                    row['quality']=list(row.get('quality',[]))+['IMPLAUSIBLE_SPEED_REJECTED']
                    continue
                if speed is not None and 0<speed<=70:
                    costs.setdefault(eid,{}).update(seconds=self.graph.edges[eid]['length']/speed,
                        source=row['source_type'],freshness='FRESH',source_time=row['observation_timestamp'],
                        congestion=row['congestion'],current_speed=speed,free_flow_speed=row['free_flow_speed'],
                        observation_id=row['observation_id'],coverage=coverage)
                    row['eligible_for_routing']=True
        for row in rows:
            if row['eligible_for_routing']:
                row['validation_status']='ELIGIBLE'
        # Closure markers are current incident states, never historical events.
        active=[r for r in rows if r['incident_type']=='ROAD_CLOSURE' and r['eligible_for_routing']]
        providers={name:('CONFIGURED_NOT_VERIFIED' if os.environ.get(name+'_API_KEY') else 'NOT_CONFIGURED') for name in ('HERE','TOMTOM')}
        sources={row['source_type'] for row in rows}
        source=next(iter(sources)) if len(sources)==1 else 'UNAVAILABLE'
        return dict(source=source,status=snapshot['status'],providers=providers,
            observations=rows,costs=costs,active_closures=active,quarantine_count=snapshot['quarantine_count'],
            quarantine=snapshot['quarantine'],offline_test_enabled=not self.recording,live_verified=False,
            errors=snapshot['errors'],freshness_policy=snapshot['freshness_policy'],
            cache_records=len(rows),cache_limit=256,provider_access='DISABLED')

    def close(self):
        self.service.stop()
