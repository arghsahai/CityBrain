"""Pilot contracts use real imported geography; research fixtures remain intact."""
from datetime import datetime, timezone, timedelta
import json
import math
from pathlib import Path
import threading
from types import SimpleNamespace
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import xml.etree.ElementTree as ET

import pytest

from citybrain.chennai.network import read_network, PILOT, NET, shortest, nearby
from citybrain.chennai.telemetry import emit, compact_event, DashboardWriter
from citybrain.chennai.traffic_providers import ReplayProvider, TrafficObservation, HEREProvider, TomTomProvider
from citybrain.chennai.gps import GPSObservation, replay
from citybrain.chennai.server import make_server, FrameReader


@pytest.fixture(scope='module')
def net():
    return read_network()


def test_osm_source_and_projection(net):
    root = ET.parse(PILOT/'network/chennai.osm.xml').getroot()
    assert root.tag == 'osm'
    campus = root.find("way[@id='336095563']")
    assert campus is not None
    assert any(t.get('v') == 'Vellore Institute of Technology - Chennai' for t in campus.findall('tag'))
    x,y = net.convertLonLat2XY(80.154,12.8408)
    assert net.convertXY2LonLat(x,y) == pytest.approx((80.154,12.8408),abs=1e-7)
    assert len(net.getTrafficLights()) == 2


def test_catalogue_and_hospital_reachability(net):
    meta=json.loads((PILOT/'network/metadata.json').read_text())
    assert len(meta['routes']) >= 2
    assert len({tuple(p) for p in meta['routes'].values()}) == len(meta['routes'])
    for path in meta['routes'].values():
        assert path[0] == meta['origin_edge']
        assert path[-1] == meta['hospital']['destination_edge']
        assert len(path) == len(set(path))
        for edge_id in path:
            assert net.getEdge(edge_id).allows('emergency')
        for a,b in zip(path,path[1:]):
            assert net.getEdge(b) in net.getEdge(a).getOutgoing()
            assert any(c.allows('emergency') for c in net.getEdge(a).getOutgoing()[net.getEdge(b)])
    for hospital in meta['hospitals']:
        assert shortest(net,meta['origin_edge'],hospital['destination_edge'])
        assert hospital['road_access_distance_m'] < 250
        assert 'SIMULATED' in hospital['availability_source']
        assert hospital['emergency_services'].startswith('UNAVAILABLE')


def test_synthetic_profiles_use_valid_routes(tmp_path,net):
    from citybrain.chennai.scenario import prepare, PROFILES
    counts=[]
    for profile in PROFILES:
        cfg,_=prepare(tmp_path/profile,profile)
        routes=ET.parse(cfg.parent/'traffic.rou.xml').getroot()
        counts.append(len(routes.findall('vehicle')))
        times=[float(v.get('depart')) for v in routes.findall('vehicle')]
        assert times == sorted(times)
        assert routes.find("vehicle[@id='ambulance_chennai']") is not None
        for route in routes.findall('route'):
            path=route.get('edges').split()
            assert all(net.getEdge(b) in net.getEdge(a).getOutgoing() for a,b in zip(path,path[1:]))
    assert counts[0] < counts[1] < counts[2]


def test_telemetry_failure_does_not_reach_runtime(tmp_path):
    runtime=SimpleNamespace(core=SimpleNamespace(traci=object()),now=20,active_plan='untouched')
    assert emit(runtime,[],tmp_path/'observations.jsonl') is False
    assert runtime.active_plan == 'untouched'


def test_dashboard_projection_keeps_execution_and_decisions():
    event=dict(action='ROUTE_EXECUTION',active_plan={'route':['a'],'recommendations':{'traffic':['large']}},
        context={'planner_state':{'roads':{'a':{'speed':1}},'routes':{'r':['a']}}},
        execution={'verification':'VERIFIED','observed_suffix':['a']},
        planner_result={'candidate_scores':{'r':{'final_score':4,'components':['large']}}})
    compact=compact_event(event)
    assert compact['execution'] == event['execution']
    assert compact['planner_result']['candidate_scores']['r']['final_score'] == 4
    assert event['active_plan']['recommendations']
    assert compact['context']['planner_state']['roads'] == {}


def test_dashboard_write_failure_is_isolated(tmp_path):
    class Writer:
        def append(self,record): self.record=record
        def summary(self,value): self.value=value
    raw=Writer();writer=DashboardWriter(raw,tmp_path/'missing/events.jsonl')
    writer.append({'action':'TERMINAL'})
    assert raw.record == {'action':'TERMINAL'}
    assert writer.failures == 1


def test_gps_consent_stop_and_retention():
    now=datetime.now(timezone.utc)
    row=dict(vehicle_id='replay-only',longitude=80.154,latitude=12.8408,timestamp=now.isoformat(),
        speed_mps=2,accuracy_m=5,consent=True,session_active=True)
    assert len(replay([row],now)) == 1
    assert replay([row],now+timedelta(seconds=121)) == []
    for key in ('consent','session_active'):
        with pytest.raises(ValueError): GPSObservation(**dict(row,**{key:False}))
    with pytest.raises(ValueError): GPSObservation(**dict(row,longitude=float('nan')))
    with pytest.raises(ValueError): replay([row],now,retention_seconds=-1)


def test_provider_explicit_matching_and_freshness(tmp_path,net):
    edge=net.getEdges()[0];lon,lat=net.convertXY2LonLat(*edge.getShape()[0])
    now=datetime.now(timezone.utc)
    row=dict(segment_id='fixture',longitude=lon,latitude=lat,speed_mps=5,free_flow_speed_mps=10,
        travel_time_s=20,congestion=0.5,incident='UNKNOWN',provider_timestamp=now.isoformat())
    fixture=tmp_path/'traffic.json';fixture.write_text(json.dumps([row]))
    matched=ReplayProvider(fixture,net,{'fixture':edge.getID()}).observations(now)['observations'][0]
    assert matched['match_validated'] and matched['fresh'] and matched['source']=='REPLAY'
    assert matched['applied_to_sumo'] is False
    assert not ReplayProvider(fixture,net,{}).observations(now)['observations'][0]['match_validated']
    assert not ReplayProvider(fixture,net,{'fixture':edge.getID()}).observations(now+timedelta(seconds=121))['observations'][0]['fresh']
    for provider in [HEREProvider(),TomTomProvider()]:
        assert provider.observations(now)['source']=='UNAVAILABLE'
    with pytest.raises(ValueError): TrafficObservation(**dict(row,speed_mps=-1))


def test_bundled_replay_uses_recorded_clock_and_matches(net):
    mapping=json.loads((PILOT/'scenarios/traffic-mapping.json').read_text())
    result=ReplayProvider(PILOT/'scenarios/traffic-replay.json',net,mapping).observations(
        datetime(2026,10,16,0,1,tzinfo=timezone.utc))
    assert result['observations'][0]['match_validated']
    assert result['observations'][0]['fresh']


def test_frame_partial_tail(tmp_path):
    path=tmp_path/'frames.jsonl';path.write_text('{"simulation_time":1}\n{"simulation_time":')
    reader=FrameReader(path)
    assert reader.at()['simulation_time']==1
    with path.open('a') as stream:stream.write('2}\n')
    assert reader.at()['simulation_time']==2
    assert reader.at(1)['simulation_time']==1


def test_read_only_api_and_replay(tmp_path):
    (tmp_path/'dashboard.jsonl').write_text(json.dumps(dict(action='PLAN_ACCEPTED',simulation_time=10,
        accepted_plan={'route':['a'],'revision':0}))+'\n')
    (tmp_path/'telemetry.jsonl').write_text('\n'.join(json.dumps(dict(simulation_time=t,source='SUMO_SIMULATED',vehicles=[])) for t in [5,10,15])+'\n')
    server=make_server(tmp_path,port=0,replay=True)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        with urlopen(base+'/api/state?at=6') as response:
            data=json.load(response)
        assert data['chennai']['simulation_time']==5
        assert data['plan'] is None
        assert data['playback']=='REPLAY'
        with urlopen(base+'/api/geography') as response:assert 'roads' in json.load(response)
        with urlopen(base) as response:assert b'CHENNAI DIGITAL TWIN' in response.read()
        for route in ['/api/state?at=nan','/api/state?at=-1','/vendor/../../../../requirements.txt']:
            with pytest.raises(HTTPError):urlopen(base+route)
        with pytest.raises(HTTPError) as error:urlopen(Request(base+'/api/state',method='POST'))
        assert error.value.code==501
    finally:
        server.shutdown();server.server_close();thread.join()


def test_protected_evidence_output():
    from citybrain.chennai.run import run
    from citybrain.chennai.network import ROOT
    with pytest.raises(ValueError,match='historical'):
        run(ROOT/'experiments/results/chennai-forbidden',serve=False)


def test_historical_integrity():
    from citybrain.chennai.validate import historical_integrity
    result=historical_integrity()
    assert result['expected']==result['actual']==2172
