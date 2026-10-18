"""Advisory pipeline contracts. HTTP is always mocked; no coverage is inferred."""
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from email.message import Message
import json
from pathlib import Path
import threading
import time
from urllib.error import HTTPError, URLError

import pytest

from citybrain.chennai.traffic import TrafficObservation, HERETrafficProvider, TomTomTrafficProvider, ReplayTrafficProvider
from citybrain.chennai.traffic.provider import FetchResult, retry_delay
from citybrain.chennai.traffic.normalization import here_rows, tomtom_row, kmh_to_mps
from citybrain.chennai.traffic.matching import RoadMatcher
from citybrain.chennai.traffic.freshness import FreshnessPolicy
from citybrain.chennai.traffic.service import TrafficService
from citybrain.chennai.network import read_network, PILOT

NOW=datetime(2026,10,16,tzinfo=timezone.utc)


def observation(**kwargs):
    return TrafficObservation(**dict(dict(observation_id='o1',provider='TEST',provider_segment_id='s1',
        road_geometry=((.0001,0),(.0009,0)),direction='FORWARD',retrieved_at=NOW,
        observation_timestamp=NOW,source_type='SYNTHETIC_SAMPLE',current_speed=5),**kwargs))


def here_payload():
    return dict(sourceUpdated=NOW.isoformat(),results=[dict(location={'shape':{'links':[{'points':[{'lng':.0001,'lat':0},{'lng':.0009,'lat':0}]}]}},currentFlow={'speed':5,'freeFlow':10,'jamFactor':4,'traversability':'open'})])


def tomtom_payload():
    return {'flowSegmentData':dict(currentSpeed=36,freeFlowSpeed=72,currentTravelTime=20,freeFlowTravelTime=10,roadClosure=True,coordinates={'coordinate':[{'longitude':80.15,'latitude':12.84},{'longitude':80.151,'latitude':12.84}]})}


@pytest.mark.parametrize('provider',[HERETrafficProvider,TomTomTrafficProvider])
def test_credentials_are_not_authorization(provider,monkeypatch):
    monkeypatch.delenv(provider.env_key,raising=False)
    def forbidden(*args):raise AssertionError('No request authorized')
    assert provider(transport=forbidden).fetch(NOW).status=='NOT_CONFIGURED'
    monkeypatch.setenv(provider.env_key,'secret')
    assert provider(transport=forbidden).fetch(NOW).status=='READY_BUT_NOT_TESTED'
    assert provider(api_key='',authorized=True,transport=forbidden).fetch(NOW).status=='NOT_CONFIGURED'


@pytest.mark.parametrize('provider,payload',[(HERETrafficProvider,here_payload),(TomTomTrafficProvider,tomtom_payload)])
def test_mocked_adapter_success(provider,payload):
    calls=[]
    def transport(endpoint,params,timeout):
        calls.append((endpoint,params,timeout));return payload()
    result=provider(api_key='mock',authorized=True,transport=transport).fetch(NOW)
    assert result.status=='FETCHED' and len(result.observations)==1
    assert calls[0][2]==5
    assert result.observations[0].source_type in {'HERE_LIVE','TOMTOM_LIVE'}
    if provider is HERETrafficProvider:
        assert calls[0][1]['locationReferencing']=='shape'
        assert result.observations[0].congestion==.4
    else:
        assert calls[0][1]['unit']=='kmph'
        assert result.observations[0].current_speed==10
        assert result.observations[0].observation_timestamp is None
        assert result.observations[0].direction=='UNKNOWN'


@pytest.mark.parametrize('provider',[HERETrafficProvider,TomTomTrafficProvider])
@pytest.mark.parametrize('code,status',[(401,'AUTHENTICATION_ERROR'),(403,'AUTHENTICATION_ERROR'),(429,'RATE_LIMITED'),(503,'PROVIDER_UNAVAILABLE')])
def test_http_errors_are_redacted(provider,code,status):
    headers=Message();headers['Retry-After']='120'
    def transport(*args):raise HTTPError('https://host/?key=secret',code,'secret',headers,None)
    result=provider(api_key='secret',authorized=True,transport=transport).fetch(NOW)
    assert result.status==status and 'secret' not in repr(result)
    if code in (429,503):assert result.retry_after==120


@pytest.mark.parametrize('error,status',[(TimeoutError('secret'),'TIMEOUT'),(URLError('secret'),'PROVIDER_UNAVAILABLE'),(ValueError('secret'),'INVALID_RESPONSE')])
def test_network_failures(error,status):
    def transport(*args):raise error
    assert HERETrafficProvider(api_key='secret',authorized=True,transport=transport).fetch(NOW).status==status


@pytest.mark.parametrize('payload',[{},[],{'results':None},{'results':'bad'}])
def test_malformed_provider_payload(payload):
    result=HERETrafficProvider(api_key='mock',authorized=True,transport=lambda *a:payload).fetch(NOW)
    assert result.status=='INVALID_RESPONSE'


def test_missing_values_and_provider_times():
    payload=here_payload();payload.pop('sourceUpdated');payload['results'][0]['currentFlow']={}
    rows,errors=here_rows(payload,NOW)
    assert not errors and rows[0].current_speed is None and rows[0].observation_timestamp is None
    assert rows[0].current_travel_time is None
    assert kmh_to_mps(36)==10 and kmh_to_mps(None) is None


@pytest.mark.parametrize('field,value',[('current_speed',-1),('free_flow_speed',float('nan')),('current_travel_time',-1),('free_flow_travel_time',float('inf')),('congestion',1.1),('current_speed',True),('observation_timestamp','2026-10-16'),('road_geometry',((200,0),(201,0))),('road_geometry',((0,0),(1,0)))])
def test_invalid_measurements(field,value):
    with pytest.raises((ValueError,TypeError)):observation(**{field:value})


def test_here_split_links_and_incidents():
    payload=here_payload();item=payload['results'][0]
    item['location']['shape']['links'].append({'points':[{'lng':.01,'lat':0},{'lng':.011,'lat':0}]})
    rows,_=here_rows(payload,NOW)
    assert len(rows)==2 and len(rows[0].road_geometry)==2
    item['incidentDetails']=dict(id='incident-1',type='construction',description={'value':'Road works'},entryTime=NOW.isoformat())
    rows,_=here_rows(payload,NOW,incidents=True)
    assert rows[0].incident_type=='construction' and rows[0].current_speed is None
    assert rows[0].incident_description=='Road works'


class Edge:
    def __init__(self,id,points,outgoing=()):self.id,self.points,self.outgoing=id,points,outgoing
    def getID(self):return self.id
    def getShape(self):return self.points
    def allows(self,kind):return True
    def getOutgoing(self):return self.outgoing


class Net:
    def __init__(self,edges):self.edges=edges
    def getEdges(self):return self.edges
    def convertLonLat2XY(self,lon,lat):return lon*100000,lat*100000


def matcher(extra=()):
    return RoadMatcher(Net([Edge('east',[(0,0),(100,0)]),*extra]))


def test_direction_and_geometry_reject_opposite_carriageway():
    match=matcher([Edge('west',[(100,0),(0,0)])]).match(observation())
    assert match.matching_status=='MATCHED' and match.matched_sumo_edges==('east',)
    reverse=replace(observation(),road_geometry=tuple(reversed(observation().road_geometry)))
    match=matcher([Edge('west',[(100,0),(0,0)])]).match(reverse)
    assert match.matched_sumo_edges==('west',)


def test_parallel_road_ambiguity():
    assert matcher([Edge('parallel',[(0,2),(100,2)])]).match(observation()).matching_status=='AMBIGUOUS'
    assert matcher([Edge('parallel',[(0,8),(100,8)])]).match(observation()).matched_sumo_edges==('east',)


def test_intersection_heading_does_not_select_cross_street():
    assert matcher([Edge('cross',[(50,-50),(50,50)])]).match(observation()).matched_sumo_edges==('east',)


@pytest.mark.parametrize('geometry,direction',[((),'FORWARD'),(((0,0),),'FORWARD'),(((.0001,0),(.00011,0)),'FORWARD'),(((.0001,0),(.0009,0)),'UNKNOWN')])
def test_insufficient_geometry(geometry,direction):
    assert matcher().match(observation(road_geometry=geometry,direction=direction)).matching_status=='INSUFFICIENT_DATA'


def test_multi_edge_connected_path_and_disconnection():
    second=Edge('b',[(50,0),(100,0)])
    first=Edge('a',[(0,0),(50,0)],[second])
    result=RoadMatcher(Net([first,second])).match(observation())
    assert result.matching_status=='MATCHED' and result.matched_sumo_edges==('a','b')
    first.outgoing=[]
    assert RoadMatcher(Net([first,second])).match(observation()).matching_status=='UNMATCHED'


def test_actual_chennai_geometry():
    provider=ReplayTrafficProvider(PILOT/'scenarios/traffic-sample-v22.json')
    result=RoadMatcher(read_network()).match(provider.records[0])
    assert result.matching_status=='MATCHED' and result.matched_sumo_edges==('-1192027270',)
    assert result.matching_confidence > .99


@pytest.mark.parametrize('age,status',[(0,'FRESH'),(120,'FRESH'),(121,'STALE'),(600,'STALE'),(601,'EXPIRED'),(-4,'FRESH'),(-6,'UNKNOWN')])
def test_freshness(age,status):
    assert FreshnessPolicy().classify(NOW-timedelta(seconds=age),NOW)[0]==status


def test_missing_time_is_unknown():
    assert FreshnessPolicy().classify(None,NOW)==('UNKNOWN',None,'MISSING_SOURCE_TIME')
    with pytest.raises(ValueError):FreshnessPolicy(expired_seconds=10)


@pytest.mark.parametrize('provenance,source',[('SYNTHETIC_SAMPLE','SYNTHETIC_SAMPLE'),('RECORDED_PROVIDER_DATA','REPLAY'),('REPLAY','REPLAY')])
def test_replay_validation_order_provenance(tmp_path,provenance,source):
    old=observation();new=replace(old,observation_id='o2',observation_timestamp=NOW+timedelta(seconds=20))
    path=tmp_path/'replay.json'
    def row(o):
        data=o.to_dict();data.pop('applied_to_sumo');return data
    path.write_text(json.dumps(dict(provenance=provenance,observations=[row(new),{'broken':True},row(old)])))
    provider=ReplayTrafficProvider(path)
    assert provider.errors==['INVALID_REPLAY_RECORD:1']
    fetched=provider.fetch(NOW)
    assert len(fetched.observations)==1 and fetched.observations[0].source_type==source
    assert len(provider.fetch(NOW+timedelta(seconds=20)).observations)==1
    assert provider.fetch(NOW+timedelta(seconds=20)).observations==[]


class Provider:
    name='TEST'
    def __init__(self,result):self.result=result;self.calls=0
    def fetch(self,now):self.calls+=1;return self.result


def test_cache_duplicates_out_of_order_outage_and_expiry():
    provider=Provider(FetchResult([observation()],'FETCHED'))
    service=TrafficService(provider,matcher(),clock=lambda:NOW)
    service.poll_once();service.poll_once()
    assert service.snapshot()['duplicates']==1
    provider.result=FetchResult([observation(observation_id='older',observation_timestamp=NOW-timedelta(seconds=1))],'FETCHED')
    service.poll_once()
    assert service.snapshot()['out_of_order']==1
    provider.result=FetchResult(status='PROVIDER_UNAVAILABLE',errors=['OFFLINE'])
    service.poll_once()
    snapshot=service.snapshot(NOW+timedelta(seconds=601))
    assert snapshot['observations'][0]['freshness_status']=='EXPIRED'
    assert snapshot['observations'][0]['observation_id']=='o1'
    assert snapshot['failed_fetches']==1 and snapshot['applied_to_sumo'] is False
    assert snapshot['display_status']!='LIVE DATA'


def test_bounded_cache_and_no_live_claim_for_replay():
    provider=Provider(FetchResult([observation(observation_id=str(i),provider_segment_id=str(i)) for i in range(10)],'REPLAY'))
    service=TrafficService(provider,matcher(),max_records=3,clock=lambda:NOW)
    service.poll_once();snapshot=service.snapshot()
    assert snapshot['observation_count']==3 and snapshot['source']=='SYNTHETIC_SAMPLE'
    assert snapshot['display_status']=='REPLAY'


def test_verified_live_requires_fresh_source_and_match():
    provider=Provider(FetchResult([observation(source_type='HERE_LIVE')],'FETCHED'))
    service=TrafficService(provider,matcher(),clock=lambda:NOW);service.poll_once()
    assert service.snapshot()['display_status']=='LIVE DATA'
    assert service.snapshot(NOW+timedelta(seconds=121))['display_status']!='LIVE DATA'
    provider.result=FetchResult([observation(observation_id='no-time',provider_segment_id='other',source_type='TOMTOM_LIVE',observation_timestamp=None,direction='UNKNOWN')],'FETCHED')
    service=TrafficService(provider,matcher(),clock=lambda:NOW);service.poll_once()
    assert service.snapshot()['match_status']=='NO VERIFIED ROAD MATCHES'
    assert service.snapshot()['display_status']!='LIVE DATA'


def test_fetch_never_blocks_snapshot_or_shutdown_and_no_overlap():
    entered,release=threading.Event(),threading.Event()
    provider=Provider(FetchResult())
    def fetch(now):
        provider.calls+=1;entered.set();release.wait(2);return FetchResult([observation()],'FETCHED')
    provider.fetch=fetch
    service=TrafficService(provider,matcher(),clock=lambda:NOW)
    service.start();service.start();assert entered.wait(1)
    start=time.monotonic();service.snapshot();service.poll_once();service.stop()
    assert time.monotonic()-start < .1 and provider.calls==1
    release.set();service._thread.join(1)
    assert not service._thread.is_alive() and not service.snapshot()['observations']


def test_rate_limit_delay_and_date_header():
    provider=Provider(FetchResult(status='RATE_LIMITED',retry_after=300))
    service=TrafficService(provider,matcher(),clock=lambda:NOW)
    assert service.poll_once()==300
    assert retry_delay('Fri, 16 Oct 2026 00:05:00 GMT',NOW)==300
    assert retry_delay('invalid',NOW)==60


def test_provider_package_cannot_control_planner_or_sumo():
    import ast
    for path in (Path(__file__).parents[1]/'citybrain/chennai/traffic').glob('*.py'):
        tree=ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):
                assert not any(token in (node.module or '') for token in ('traci','citybrain.core','citybrain.planner','citybrain.main'))
            if isinstance(node,ast.Import):
                assert all(not any(token in alias.name for token in ('traci','citybrain.core','citybrain.planner','citybrain.main')) for alias in node.names)


def test_dashboard_labels_and_distinct_overlay_hooks():
    root=Path(__file__).parents[1]/'dashboard/cesium'
    html=(root/'index.html').read_text();js=(root/'app.js').read_text()
    assert 'TRAFFIC OBSERVATIONS' in html and 'LIVE TRAFFIC OBSERVATIONS' not in html
    assert 'OPT-IN EXPERIMENTAL ROUTE ADVISOR' in html
    assert 'SUMO_SIMULATED speed' in js and 'External speed' in js
    assert 'external-flow:' in js and 'external-incident:' in js
    assert 'NO VERIFIED ROAD MATCHES' in js and 'freshness_status' in js


def test_recorded_provider_is_never_live_and_kept_open_view_expires():
    from citybrain.chennai.server import presentation_frame
    provider=Provider(FetchResult([observation(source_type='HERE_LIVE')],'FETCHED'))
    service=TrafficService(provider,matcher(),clock=lambda:NOW);service.poll_once()
    frame={'external':service.snapshot()}
    replay=presentation_frame(frame,replay=True)
    assert replay['external']['source']=='REPLAY'
    assert replay['external']['observations'][0]['source_type']=='REPLAY'
    assert frame['external']['observations'][0]['source_type']=='HERE_LIVE'
    stale=presentation_frame(frame,now=NOW+timedelta(seconds=700))
    assert stale['external']['observations'][0]['freshness_status']=='EXPIRED'
    assert stale['external']['display_status']!='LIVE DATA'


def test_nonfinite_raw_measurements_cannot_break_sumo_telemetry():
    payload=here_payload();payload['results'][0]['currentFlow']['speedUncapped']=float('nan')
    rows,errors=here_rows(payload,NOW)
    assert not rows and errors==['INVALID_RECORD:0']


def test_connected_parallel_roads_are_still_ambiguous_mid_segment():
    parallel=Edge('parallel',[(0,2),(100,2)])
    first=Edge('east',[(0,0),(100,0)],[parallel])
    assert RoadMatcher(Net([first,parallel])).match(observation()).matching_status=='AMBIGUOUS'
