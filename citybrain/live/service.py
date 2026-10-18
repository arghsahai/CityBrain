"""Validated live-data prototype state, independent of simulation execution."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
import math
import secrets
import threading
from citybrain.chennai.network import PILOT
from citybrain.agents.ambulance_agent import AmbulanceAgent
from citybrain.agents.hospital_agent import HospitalAgent
from citybrain.agents.traffic_agent import TrafficAgent
from citybrain.agents.police_agent import PoliceAgent
from citybrain.agents.signal_agent import SignalAgent
from citybrain.models.emergency import Emergency
from .graph import PilotGraph, LiveError, coordinate
from .store import Store


def text(value, maximum, *, required=False):
    if not isinstance(value,str) or len(value)>maximum or any(ord(c)<32 and c not in '\n\t' for c in value):
        raise LiveError('INVALID_TEXT')
    value=value.strip()
    if required and not value:
        raise LiveError('REQUIRED_TEXT')
    return value


class LiveService:
    def __init__(self,store=None,clock=None,graph=None,traffic=None):
        self.store=store or Store()
        self.clock=clock or (lambda:datetime.now(timezone.utc))
        self.graph=graph or PilotGraph()
        self.traffic=traffic
        self.lock=threading.RLock()
        self.ambulance=None
        self.current=None
        self.history=[]
        self.last_change=None
        self.route_request=None
        raw=json.loads((PILOT/'network/metadata.json').read_text())['hospitals']
        self.directory=[dict(id=h['id'],name=h['name'],coordinates=[h['longitude'],h['latitude']],
            address=None,facility_type='OSM hospital tag',services='UNVERIFIED',source=h['location_source'],
            last_verified_at=None,destination_edge=h['destination_edge'],
            road_access='ROAD LEVEL ONLY — entrance and final driveway unverified') for h in raw]

    def record_history(self,action,reason,route=None):
        entry=dict(at=self.iso(),action=action,reason=reason)
        if route is not None:
            entry['route']=route
        if self.history:
            previous=self.history[-1]
            age=(self.clock()-datetime.fromisoformat(previous['at'])).total_seconds()
            if age<60 and all(previous.get(k)==entry.get(k) for k in ('action','reason','route')):
                return
        self.history.append(entry)
        self.history=self.history[-50:]

    def now(self):
        return self.clock().timestamp()

    def iso(self):
        return self.clock().isoformat()

    def audit(self,action,target,actor):
        self.store.put('audit',secrets.token_hex(8),dict(action=action,target=target,actor=actor,at=self.iso()),self.now(),2000)

    def submit(self,body):
        with self.lock:
            self.store.prune(self.now())
            if body.get('test') is not True or body.get('confirmed') is not True:
                raise LiveError('TEST_AND_LOCATION_CONFIRMATION_REQUIRED')
            point=coordinate(body.get('coordinates'))
            if not self.graph.in_bounds(point):
                raise LiveError('OUTSIDE_ROUTING_PILOT')
            kind=body.get('type')
            if not isinstance(kind,str) or kind not in {'ROAD_COLLISION','ROAD_HAZARD','OTHER_TEST'}:
                raise LiveError('INVALID_INCIDENT_TYPE')
            description=text(body.get('description',''),300)
            for old in self.store.rows('incidents'):
                d=math.hypot((point[0]-old['coordinates'][0])*108500,(point[1]-old['coordinates'][1])*111320)
                if d<30 and old['type']==kind and self.now()-old['created_epoch']<300 and old['status'] not in {'REJECTED','RESOLVED'}:
                    raise LiveError('POSSIBLE_DUPLICATE', 'A nearby report of this type was submitted within five minutes')
            row=dict(id=secrets.token_hex(8),coordinates=point,type=kind,description=description,
                status='PENDING_VERIFICATION',source='PUBLIC_TEST_REPORT',created_at=self.iso(),created_epoch=self.now())
            self.store.put('incidents',row['id'],row,self.now())
            self.audit('SUBMITTED',row['id'],'public')
            return dict(id=row['id'],status=row['status'],source=row['source'])

    def verify(self,key,status,actor='operator'):
        with self.lock:
            self.store.prune(self.now())
            key=text(key,64,required=True)
            row=self.store.get('incidents',key)
            if row is None:
                raise LiveError('INCIDENT_NOT_FOUND')
            allowed={'PENDING_VERIFICATION':{'VERIFIED_FOR_TESTING','REJECTED'},'VERIFIED_FOR_TESTING':{'RESOLVED','REJECTED'}}
            if status not in allowed.get(row['status'],set()):
                raise LiveError('INVALID_INCIDENT_TRANSITION')
            row.update(status=status,verified_at=self.iso())
            self.store.put('incidents',key,row,self.now())
            self.audit(status,key,actor)
            if self.current and self.current['incident_id']==key and status!='VERIFIED_FOR_TESTING':
                self.current.update(status='CANCELLED',reason='INCIDENT_NO_LONGER_VERIFIED')
                self.route_request=None
            return row

    def position(self,body):
        with self.lock:
            if body.get('source')!='USER_SELECTED':
                raise LiveError('AUTHORIZED_GPS_NOT_IMPLEMENTED')
            snap=self.graph.snap(body.get('coordinates'),body.get('edge'))
            self.ambulance=dict(id='TEST_AMBULANCE',available=True,position=snap,source='USER_SELECTED',updated_at=self.iso())
            self.audit('TEST_AMBULANCE_POSITION','TEST_AMBULANCE','operator')
            if self.route_request:
                self.reassess('POSITION_CHANGED',force=True)
            return self.ambulance

    def hospitals(self):
        result=[]
        for hospital in self.directory:
            row=self.store.get('hospital',hospital['id'])
            recent=row and 0<=self.now()-row['updated_epoch']<=900
            result.append(dict(hospital,status=row if recent else None,
                availability='STAFF_REPORTED' if recent else 'AVAILABILITY_UNKNOWN',
                freshness='FRESH' if recent else 'STALE' if row else 'UNKNOWN'))
        return result

    def hospital_update(self,key,body,actor):
        with self.lock:
            if key not in {h['id'] for h in self.directory}:
                raise LiveError('HOSPITAL_NOT_FOUND')
            for field in ('accepting','trauma','icu'):
                if body.get(field) is not None and type(body[field]) is not bool:
                    raise LiveError('INVALID_HOSPITAL_STATUS')
            beds=body.get('beds')
            if beds is not None and (type(beds) is not int or not 0<=beds<=10000):
                raise LiveError('INVALID_BED_COUNT')
            row=dict(accepting=body.get('accepting'),trauma=body.get('trauma'),icu=body.get('icu'),beds=beds,
                     notes=text(body.get('notes',''),200),updated_at=self.iso(),updated_epoch=self.now(),
                     source='STAFF_REPORTED',operator=actor)
            self.store.put('hospital',key,row,self.now(),100)
            self.audit('HOSPITAL_STATUS_UPDATE',key,actor)
            if self.route_request:
                self.reassess('HOSPITAL_STATUS_CHANGED',force=True)
            return row

    def _traffic(self):
        try:
            if self.traffic:
                return self.traffic.snapshot()
        except Exception:
            pass  # No provider exception text or credentials cross this boundary.
        return dict(source='UNAVAILABLE',observations=[],costs={},providers={},errors=['TRAFFIC_UNAVAILABLE'])

    def recommend(self,body):
        with self.lock:
            if body.get('leg') not in {'AMBULANCE_TO_INCIDENT','INCIDENT_TO_HOSPITAL'}:
                raise LiveError('INVALID_JOURNEY_LEG')
            if type(body.get('require_icu',False)) is not bool or type(body.get('require_trauma',False)) is not bool:
                raise LiveError('INVALID_SERVICE_REQUIREMENT')
            result=self._compute(body)
            self.route_request=dict(body)
            return self._accept_candidate(result,'INITIAL_RECOMMENDATION')

    def _compute(self,body):
        self.store.prune(self.now())
        incident=self.store.get('incidents',text(body.get('incident_id',''),64,required=True))
        if not incident or incident['status']!='VERIFIED_FOR_TESTING':
            raise LiveError('VERIFIED_TEST_INCIDENT_REQUIRED')
        emergency=Emergency(incident['id'],'TEST_INCIDENT','TEST',incident['type'])
        selected=AmbulanceAgent().select(emergency,{'ambulances':[self.ambulance] if self.ambulance else []})
        if not selected.success:
            raise LiveError('TEST_AMBULANCE_POSITION_REQUIRED')
        destination=self.graph.snap(incident['coordinates'],body.get('incident_edge'))
        traffic=self._traffic()
        costs=traffic.get('costs',{})
        if body['leg']=='AMBULANCE_TO_INCIDENT':
            route=self.graph.route(self.ambulance['position'],destination,costs)
            hospital=None
        else:
            # Second leg begins at the CURRENT test ambulance position; operator
            # must explicitly confirm the vehicle has reached the incident road.
            if body.get('incident_arrival_confirmed') is not True:
                raise LiveError('INCIDENT_ARRIVAL_CONFIRMATION_REQUIRED')
            p,q=self.ambulance['position']['coordinates'],destination['coordinates']
            if math.hypot((p[0]-q[0])*108500,(p[1]-q[1])*111320)>50:
                raise LiveError('CURRENT_POSITION_NOT_AT_INCIDENT')
            choices=[]
            for h in self.hospitals():
                status=h['status']
                if (not status or status['accepting'] is not True or status['beds'] is None or status['beds']<=0 or
                    body.get('require_trauma') and status['trauma'] is not True or
                    body.get('require_icu') and status['icu'] is not True):
                    continue
                if body.get('hospital_id') and body['hospital_id']!=h['id']:
                    continue
                eid=h['destination_edge']
                if eid not in self.graph.edges:
                    continue
                # Project real facility coordinates onto its retained access road.
                from citybrain.chennai.traffic.matching import projection
                xy=self.graph.net.convertLonLat2XY(*h['coordinates'])
                e=self.graph.edges[eid]
                dist,along=min((lambda part:(projection(xy,*part[:3])[0],part[3]+projection(xy,*part[:3])[1]))(part) for part in e['parts'])
                end=dict(edge=eid,fraction=along/e['geometry_length'])
                try:
                    candidate=self.graph.route(self.ambulance['position'],end,costs)
                except LiveError:
                    continue
                choices.append((candidate['eta_seconds'],h['id'],h,candidate))
            if not choices:
                raise LiveError('NO_RECENT_SUITABLE_REACHABLE_HOSPITAL')
            choices.sort(key=lambda row:row[:2])
            if body.get('require_icu'):
                picked=HospitalAgent().select(emergency,{'hospitals':[dict(id=r[1],icu_available=True) for r in choices]})
                chosen=next(r for r in choices if r[1]==picked.selected['id'])
            else:
                chosen=choices[0]  # Live suitability adapter: do not invent ICU availability.
            _,_,hospital,route=chosen
        roads={eid:dict(congestion='UNKNOWN',to=self.graph.edges[eid]['to']) for eid in route['route']}
        agents=dict(ambulance=asdict(selected),traffic=asdict(TrafficAgent().assess({'roads':roads})),
                    police=asdict(PoliceAgent().recommend(emergency)),signal=asdict(SignalAgent().recommend(route['route'],{'roads':roads})),
                    hospital=dict(reason='RECENT_STAFF_REPORT_AND_REACHABILITY' if hospital else 'NOT_REQUIRED_FOR_FIRST_LEG'))
        agents['traffic'].update(eligible_observations=sum(r.get('eligible_for_routing',False) for r in traffic['observations']),
            route_cost_sources=sorted({c['source'] for c in route['components']}))
        sources=dict(ambulance='USER_SELECTED',traffic=traffic['source'],
            hospital='STAFF_REPORTED' if hospital else 'UNAVAILABLE',
            police='PUBLIC_TEST_REPORT',signal='OSM_IMPORTED_JUNCTIONS')
        source_times=dict(ambulance=self.ambulance['updated_at'],
            traffic=sorted({r['observation_timestamp'] for r in traffic['observations'] if r.get('eligible_for_routing') and r.get('observation_timestamp')}),
            hospital=hospital['status']['updated_at'] if hospital else None,
            police=incident['created_at'],signal=None)
        for name,row in agents.items():
            row.update(source=sources[name],source_updated_at=source_times[name],assessment_at=self.iso(),
                validity='PROTOTYPE_ADVISORY',missing='No field validation or authorized operational integration')
        return dict(route,incident_id=incident['id'],leg=body['leg'],hospital=hospital,
            position=self.ambulance['position'],agents=agents,traffic_source=traffic['source'])

    def _accept_candidate(self,result,reason):
        self.current=dict(result,id=secrets.token_hex(8),status='PENDING_OPERATOR_REVIEW',reason=reason,updated_at=self.iso())
        self.last_change=self.now()
        self.record_history('RECOMMENDED',reason,result['route'])
        return self.current

    def reassess(self,trigger='TRAFFIC_CHANGED',force=False):
        with self.lock:
            if not self.route_request:
                return None
            try:
                candidate=self._compute(self.route_request)
            except LiveError as error:
                self.current=dict(self.current or {},status='UNAVAILABLE',reason=error.code,updated_at=self.iso())
                self.record_history('UNAVAILABLE',error.code)
                return self.current
            old=self.current
            # Re-score the current route with CURRENT data before comparing;
            # old cached ETA must never drive switching after traffic changes.
            costs=self._traffic().get('costs',{})
            blocked=old and any(costs.get(e,{}).get('blocked') for e in old.get('route',[]))
            old_seconds=sum((costs.get(c['edge'],{}).get('seconds',self.graph.edges[c['edge']]['length']/self.graph.edges[c['edge']]['speed']))*c['fraction'] for c in old.get('components',[])) if old else math.inf
            changed=not old or candidate['route']!=old.get('route') or candidate.get('hospital',{} )!=old.get('hospital',{})
            improvement=old_seconds-candidate['eta_seconds']
            eligible=force or blocked or old.get('status') in {'UNAVAILABLE','CANCELLED'} or (
                changed and self.now()-(self.last_change or 0)>=60 and improvement>=max(30,old_seconds*.1))
            if eligible:
                return self._accept_candidate(candidate,trigger)
            # Same route refreshes provenance/ETA without retaining approval on
            # changed inputs. A kept alternative retains geometry but re-scores.
            if not changed:
                inputs_changed=old.get('components')!=candidate['components']
                status='PENDING_OPERATOR_REVIEW' if inputs_changed else old['status']
                self.current=dict(old,**candidate,id=secrets.token_hex(8) if inputs_changed else old['id'],status=status,reason='KEEP_SAME_VALID_ROUTE',updated_at=self.iso())
            else:
                previous_components=[dict(c) for c in self.current['components']]
                previous_status=self.current['status']
                self.current.update(reason='KEEP_COOLDOWN_OR_INSUFFICIENT_IMPROVEMENT',eta_seconds=old_seconds)
                self.current['traffic_source']=candidate['traffic_source']
                for c in self.current['components']:
                    row=costs.get(c['edge'],{})
                    c.update(seconds=row.get('seconds',self.graph.edges[c['edge']]['length']/self.graph.edges[c['edge']]['speed'])*c['fraction'],source=row.get('source','ESTIMATED_FREE_FLOW'),freshness=row.get('freshness','UNKNOWN'))
                if previous_components!=self.current['components']:
                    self.current.update(id=secrets.token_hex(8),status='PENDING_OPERATOR_REVIEW')
                else:
                    self.current['status']=previous_status
                self.current['estimated_edges']=sum(c['source']=='ESTIMATED_FREE_FLOW' for c in self.current['components'])
                self.current['observed_edges']=len(self.current['components'])-self.current['estimated_edges']
            self.record_history('KEEP',self.current['reason'])
            return self.current

    def transition(self,status,expected_id=None):
        with self.lock:
            if status in {'APPROVED','ACKNOWLEDGED'} and not isinstance(expected_id,str):
                raise LiveError('RECOMMENDATION_ID_REQUIRED')
            if self.route_request and status in {'APPROVED','ACKNOWLEDGED'}:
                self.reassess('PRE_APPROVAL_VALIDATION')
            if expected_id is not None and (not self.current or self.current['id']!=expected_id):
                raise LiveError('RECOMMENDATION_CHANGED_REVIEW_AGAIN')
            allowed={'PENDING_OPERATOR_REVIEW':{'APPROVED','CANCELLED'},'APPROVED':{'ACKNOWLEDGED','CANCELLED'},'ACKNOWLEDGED':{'ARRIVAL_REPORTED','CANCELLED'}}
            if not self.current or status not in allowed.get(self.current['status'],set()):
                raise LiveError('INVALID_RECOMMENDATION_TRANSITION')
            self.current.update(status=status)
            self.audit(status,self.current['id'],'operator')
            if status in {'CANCELLED','ARRIVAL_REPORTED'}:
                self.route_request=None
            return self.current

    def state(self,operator=False):
        with self.lock:
            self.store.prune(self.now())
            if self.route_request:
                self.reassess('FRESHNESS_REASSESSMENT')
            traffic=self._traffic()
            return dict(mode='LIVE DATA',traffic=traffic,provider_access='DISABLED — NO AUTHORIZED API REQUESTS',
                hospitals=self.hospitals(),incidents=self.store.rows('incidents') if operator else [],
                ambulance=self.ambulance if operator else None,recommendation=self.current if operator else None,
                history=self.history if operator else [],signal='ADVISORY_ONLY',
                warning='Experimental research platform. No real dispatch. For genuine Tamil Nadu emergencies call 108.')
