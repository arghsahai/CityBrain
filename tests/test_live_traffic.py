from dataclasses import replace
from datetime import datetime,timedelta,timezone
import json
import socket
import pytest
from citybrain.chennai.network import PILOT
from citybrain.chennai.traffic.models import TrafficObservation
from citybrain.chennai.traffic.provider import FetchResult
from citybrain.live.traffic import OfflineTraffic,edge_coverage
from citybrain.live.service import LiveService
from citybrain.live.graph import LiveError


@pytest.fixture
def configured():
    now=[datetime(2026,10,19,tzinfo=timezone.utc)]
    s=LiveService(clock=lambda:now[0])
    t=s.traffic=OfflineTraffic(s.graph,s.clock)
    m=json.loads((PILOT/'network/metadata.json').read_text())
    path=next(iter(m['routes'].values()))
    a,b=path[0],path[-1]
    row=s.submit(dict(test=True,confirmed=True,type='ROAD_COLLISION',coordinates=s.graph.point_at(b,.5)))
    s.verify(row['id'],'VERIFIED_FOR_TESTING')
    s.position(dict(source='USER_SELECTED',coordinates=s.graph.point_at(a,.5),edge=a))
    request=dict(leg='AMBULANCE_TO_INCIDENT',incident_id=row['id'],incident_edge=b)
    s.recommend(request)
    yield s,t,now
    t.close();s.store.close()


def usable(s,t):
    for eid in s.current['route'][1:-1]:
        snap=t.inject(dict(edge=eid,condition='FLOW'))
        if eid in snap['costs']:
            return eid
    raise AssertionError('No eligible retained route edge')


def test_closure_reopening_future_recovery_and_no_network(configured,monkeypatch):
    s,t,now=configured
    def forbidden(*a,**k):
        raise AssertionError('network requested')
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setenv('HERE_API_KEY','not-a-real-key')
    eid=usable(s,t)
    assert t.snapshot()['providers']['HERE']=='CONFIGURED_NOT_VERIFIED'
    before=t.snapshot()['costs'][eid]['seconds']
    for condition,expected in [('CLOSURE',1),('REOPEN',0),('CLOSURE',1)]:
        now[0]+=timedelta(seconds=1)
        result=t.inject(dict(edge=eid,condition=condition))
        assert len(result['active_closures'])==expected
        assert bool(result['costs'].get(eid,{}).get('blocked'))==bool(expected)
    t.inject(dict(edge=eid,condition='FUTURE'))
    assert t.snapshot()['quarantine_count']==1
    assert t.snapshot()['costs'][eid]['seconds']==before
    now[0]+=timedelta(seconds=2)
    t.inject(dict(edge=eid,condition='FLOW'))
    assert t.snapshot()['costs'][eid]['seconds']==before
    assert t.snapshot()['live_verified'] is False
    t.inject(dict(condition='OUTAGE'))
    assert t.snapshot()['status']=='PROVIDER_UNAVAILABLE'
    assert s.state(True)['mode']=='LIVE DATA'
    now[0]+=timedelta(seconds=601)
    snapshot=t.snapshot()
    assert snapshot['costs']=={} and snapshot['active_closures']==[]
    assert all(row['freshness_status']=='EXPIRED' for row in snapshot['observations'])


def test_full_edge_coverage_not_partial_provider_coverage(configured):
    s,t,_=configured
    eid=usable(s,t)
    row=t.snapshot()['observations'][0]
    # Finite 10m observation within a longer edge cannot measure that whole edge.
    row['road_geometry']=[s.graph.point_at(eid,.4),s.graph.point_at(eid,.45)]
    assert edge_coverage(s.graph,eid,row)<.2


def test_out_of_order_missing_time_direction_and_clock_skew(configured):
    s,t,now=configured
    eid=usable(s,t)
    old=next(iter(t.service._cache.values()))
    def feed(row):
        t.queue.result=FetchResult([row],status='REPLAY');t.service.poll_once()
    now[0]+=timedelta(seconds=10)
    feed(replace(old,observation_timestamp=now[0],current_speed=4))
    expected=t.snapshot()['costs'][eid]['seconds']
    feed(replace(old,observation_timestamp=now[0]-timedelta(seconds=9),current_speed=1))
    assert t.snapshot()['costs'][eid]['seconds']==expected
    feed(replace(old,observation_timestamp=None,current_speed=1))
    assert t.snapshot()['costs'][eid]['seconds']==expected
    feed(replace(old,observation_timestamp=now[0]+timedelta(seconds=6),current_speed=1))
    assert t.snapshot()['quarantine_count']==1
    assert t.snapshot()['costs'][eid]['seconds']==expected
    now[0]+=timedelta(seconds=1)
    feed(replace(old,observation_timestamp=now[0],direction='UNKNOWN'))
    assert eid not in t.snapshot()['costs']
    now[0]+=timedelta(seconds=1)
    feed(replace(old,observation_timestamp=now[0],current_speed=3))
    assert eid in t.snapshot()['costs']


def test_deterministic_traffic_reassessment_closure_and_cooldown(configured):
    s,t,now=configured
    original=s.current['route']
    s.transition('APPROVED',s.current['id'])
    # Choose a matchable edge with a legal alternate route.
    found=None
    for eid in original[1:-1]:
        result=t.inject(dict(edge=eid,condition='CLOSURE'))
        if result['costs'].get(eid,{}).get('blocked'):
            try:
                alternative=s._compute(s.route_request)
            except LiveError:
                alternative=None
            if alternative and eid not in alternative['route']:
                found=eid;break
        t.inject(dict(edge=eid,condition='REOPEN'))
    assert found
    changed=s.reassess('KNOWN_TEST_CLOSURE')
    assert changed['status']=='PENDING_OPERATOR_REVIEW'
    assert changed['route']!=original and found not in changed['route']
    now[0]+=timedelta(seconds=1)
    t.inject(dict(edge=found,condition='REOPEN'))
    kept=s.reassess('REOPENED')
    assert kept['route']==changed['route']
    assert kept['reason']=='KEEP_COOLDOWN_OR_INSUFFICIENT_IMPROVEMENT'
    assert any(h['action']=='KEEP' for h in s.history)
    assert s.current['execution']=='RECOMMENDATION_ONLY'


def test_provider_exception_isolation_and_stale_approval(configured):
    s,t,now=configured
    eid=usable(s,t)
    s.reassess('FLOW_CHANGED')
    reviewed=s.current['id']
    now[0]+=timedelta(seconds=121)
    with pytest.raises(LiveError,match='RECOMMENDATION_CHANGED_REVIEW_AGAIN'):
        s.transition('APPROVED',reviewed)
    assert s.current['observed_edges']==0
    assert s.current['status']=='PENDING_OPERATOR_REVIEW'
    class Failing:
        def snapshot(self):
            raise RuntimeError('secret-provider-url')
    s.traffic=Failing()
    result=s.reassess('OUTAGE')
    assert result['execution']=='RECOMMENDATION_ONLY'
    assert 'secret-provider-url' not in json.dumps(s.state(True))
    assert result['traffic_source']=='UNAVAILABLE'


def test_local_recording_is_always_replay_and_keeps_original_time(configured,tmp_path):
    s,t,now=configured
    eid=usable(s,t)
    old=next(iter(t.service._cache.values()))
    from dataclasses import asdict
    row=asdict(old)
    row['observation_timestamp']=old.observation_timestamp.isoformat()
    row['retrieved_at']=old.retrieved_at.isoformat()
    row['source_type']='HERE_LIVE'
    path=tmp_path/'recording.json'
    path.write_text(json.dumps(dict(provenance='RECORDED_PROVIDER_DATA',observations=[row])))
    recorded=OfflineTraffic(s.graph,s.clock,recording=path)
    result=recorded.snapshot()
    assert result['source']=='RECORDED_PROVIDER_REPLAY'
    assert result['live_verified'] is False
    assert result['observations'][0]['observation_timestamp']==old.observation_timestamp.isoformat()
    now[0]+=timedelta(seconds=601)
    assert recorded.snapshot()['costs']=={}
    with pytest.raises(LiveError,match='SYNTHETIC_INJECTION_DISABLED'):
        recorded.inject(dict(edge=eid,condition='FLOW'))
    recorded.close()


def test_zero_speed_not_free_flow_and_bounded_cache(configured):
    s,t,now=configured
    eid=usable(s,t)
    old=next(iter(t.service._cache.values()))
    now[0]+=timedelta(seconds=1)
    t.queue.result=FetchResult([replace(old,current_speed=0,observation_timestamp=now[0])],status='REPLAY')
    t.service.poll_once()
    assert t.snapshot()['costs'][eid]['blocked'] is True
    now[0]+=timedelta(seconds=1)
    t.queue.result=FetchResult([replace(old,current_speed=999,observation_timestamp=now[0])],status='REPLAY')
    t.service.poll_once()
    assert eid not in t.snapshot()['costs']
    records=[replace(old,stream_id=str(i),observation_id=str(i)) for i in range(300)]
    t.queue.result=FetchResult(records,status='REPLAY');t.service.poll_once()
    assert t.snapshot()['cache_records']==256
    t.queue.result=FetchResult([replace(r,observation_timestamp=now[0]+timedelta(days=365)) for r in records],status='REPLAY')
    t.service.poll_once()
    assert t.snapshot()['quarantine_count']==64
