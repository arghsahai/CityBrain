"""HERE-to-live routing contracts. All transports are local mock functions."""
from datetime import datetime,timedelta,timezone
from email.message import Message
import json
from urllib.error import HTTPError
import pytest
from citybrain.live.here import HEREQuerySession,HERETraffic,readiness
from citybrain.live.service import LiveService
from citybrain.live.graph import BOUNDS,LiveError
from citybrain.chennai.network import PILOT

NOW=datetime(2026,10,20,tzinfo=timezone.utc)


def payload(graph,eid,now,*,speed=2,closed=False,incident=False):
    geometry=graph.edges[eid]['coordinates']
    details=dict(id='test-incident-v1',originalId='test-stable',type='roadClosure' if closed else 'construction',status='active',roadClosed=closed) if incident else dict(speed=speed,freeFlow=13,jamFactor=10 if closed else 7,confidence=.99,traversability='closed' if closed else 'open')
    return dict(sourceUpdated=now.isoformat(),results=[dict(location=dict(shape=dict(links=[dict(points=[dict(lng=p[0],lat=p[1]) for p in geometry])])),**{'incidentDetails' if incident else 'currentFlow':details})])


@pytest.fixture
def connected():
    now=[NOW]
    s=LiveService(clock=lambda:now[0])
    path=next(iter(json.loads((PILOT/'network/metadata.json').read_text())['routes'].values()))
    row=s.submit(dict(test=True,confirmed=True,type='ROAD_COLLISION',coordinates=s.graph.point_at(path[-1],.5)))
    s.verify(row['id'],'VERIFIED_FOR_TESTING')
    s.position(dict(source='USER_SELECTED',coordinates=s.graph.point_at(path[0],.5),edge=path[0]))
    request=dict(leg='AMBULANCE_TO_INCIDENT',incident_id=row['id'],incident_edge=path[-1])
    s.recommend(request)
    data={'flow':dict(sourceUpdated=NOW.isoformat(),results=[]),'incidents':dict(sourceUpdated=NOW.isoformat(),results=[])}
    calls=[]
    def transport(url,params,timeout):
        kind=url.rsplit('/',1)[-1]; calls.append(kind);return data[kind]
    t=s.traffic=HERETraffic(s.graph,s.clock,transport=transport,max_requests=20,poll_seconds=60)
    yield s,t,now,data,calls
    t.close();s.store.close()


def eligible_edge(s,t,now,data):
    for eid in s.current['route'][1:-1]:
        data['flow']=payload(s.graph,eid,now[0])
        t.queue.next_poll=now[0]
        t.service.poll_once()
        if eid in t.snapshot()['costs']:
            return eid
    raise AssertionError('No matchable route edge')


def test_key_is_not_permission(monkeypatch):
    monkeypatch.delenv('HERE_API_KEY',raising=False)
    assert readiness()['status']=='NOT_CONFIGURED'
    monkeypatch.setenv('HERE_API_KEY','secret-must-not-leak')
    assert readiness()['status']=='CONFIGURED_NOT_VERIFIED'
    feed=HEREQuerySession()
    assert feed.fetch(NOW).observations==[]
    assert sum(feed.accounting()['real_requests'].values())==0
    assert 'secret-must-not-leak' not in json.dumps(readiness())+json.dumps(feed.accounting())
    for options in [dict(authorized=True),dict(authorized=True,licensed=True,max_requests=2),dict(area=(80,12,81,13))]:
        with pytest.raises(ValueError):HEREQuerySession(**options)


def test_endpoint_budget_pacing_and_mock_labels(connected):
    s,t,now,data,calls=connected
    eid=eligible_edge(s,t,now,data)
    assert t.snapshot()['source']=='REPLAY'
    assert not t.snapshot()['live_verified']
    assert t.snapshot()['costs'][eid]['source']=='REPLAY'
    assert t.snapshot()['observations'][-1]['provider']=='HERE'
    before=len(calls)
    t.service.poll_once(); assert len(calls)==before
    limited=HEREQuerySession(transport=lambda *a:data['flow'],max_requests=1,clock=lambda:NOW)
    result=limited.fetch(NOW)
    assert result.status=='BUDGET_EXHAUSTED'
    assert limited.accounting()['attempted']=={'flow':1,'incidents':0}
    assert limited.accounting()['real_requests']=={'flow':0,'incidents':0}
    assert limited.fetch(NOW+timedelta(seconds=61)).status=='BUDGET_EXHAUSTED'


@pytest.mark.parametrize('failure,expected',[(TimeoutError('secret'),'TIMEOUT'),(ValueError('secret'),'INVALID_RESPONSE'),(RuntimeError('secret'),'PROVIDER_UNAVAILABLE')])
def test_failure_sanitization(failure,expected):
    def transport(*args):raise failure
    q=HEREQuerySession(transport=transport,max_requests=4,clock=lambda:NOW)
    r=q.fetch(NOW)
    assert r.status==expected
    assert 'secret' not in repr(r)+json.dumps(q.accounting())
    assert q.accounting()['attempted']=={'flow':1,'incidents':1}


def test_rate_limit_backoff_and_independent_accounting():
    h=Message();h['Retry-After']='180'
    def transport(*args):raise HTTPError('https://x?apiKey=secret',429,'secret',h,None)
    q=HEREQuerySession(transport=transport,max_requests=6,clock=lambda:NOW)
    assert q.fetch(NOW).status=='RATE_LIMITED'
    q.fetch(NOW+timedelta(seconds=120))
    assert sum(q.accounting()['attempted'].values())==2
    q.fetch(NOW+timedelta(seconds=181))
    assert sum(q.accounting()['attempted'].values())==4


def test_here_flow_closure_drives_alternative_and_reopening_keeps_cooldown(connected):
    s,t,now,data,_=connected
    eid=eligible_edge(s,t,now,data)
    original=list(s.current['route'])
    # Pick a legal diversion; only real directed geometry is matched.
    for candidate in original[1:-1]:
        try:
            s.graph.route(s.ambulance['position'],s.graph.snap(s.store.rows('incidents')[0]['coordinates'],original[-1]),{candidate:{'blocked':True}})
        except LiveError:continue
        data['flow']=payload(s.graph,candidate,now[0],closed=True)
        t.queue.next_poll=now[0];t.service.poll_once()
        if t.snapshot()['costs'].get(candidate,{}).get('blocked'):
            eid=candidate;break
    else:raise AssertionError('No validated closure alternative')
    changed=s.reassess('HERE_TEST_CLOSURE')
    assert changed['route']!=original and eid not in changed['route']
    assert changed['status']=='PENDING_OPERATOR_REVIEW'
    assert changed['execution']=='RECOMMENDATION_ONLY' and changed['traffic_source']=='REPLAY'
    now[0]+=timedelta(seconds=1)
    data['flow']=payload(s.graph,eid,now[0],speed=13)
    t.queue.next_poll=now[0];t.service.poll_once()
    assert not t.snapshot()['active_closures']
    kept=s.reassess('HERE_TEST_REOPEN')
    assert kept['route']==changed['route']
    assert kept['reason']=='KEEP_COOLDOWN_OR_INSUFFICIENT_IMPROVEMENT'


def test_invalid_stale_future_partial_and_direction(connected):
    s,t,now,data,_=connected
    eid=eligible_edge(s,t,now,data)
    for change in ['missing','future','partial','reverse','historical','subsegments','invalid']:
        row=payload(s.graph,eid,now[0])
        if change=='missing':row.pop('sourceUpdated')
        if change=='future':row['sourceUpdated']=(now[0]+timedelta(days=1)).isoformat()
        if change=='partial':row['results'][0]['location']['shape']['links'][0]['points']=[dict(zip(('lng','lat'),s.graph.point_at(eid,f))) for f in [.4,.45]]
        if change=='reverse':row['results'][0]['location']['shape']['links'][0]['points'].reverse()
        if change=='historical':row['results'][0]['currentFlow']['confidence']=.5
        if change=='subsegments':row['results'][0]['currentFlow']['subSegments']=[dict(length=1,speed=2)]
        if change=='invalid':row={'bad':'payload'}
        # Independent session ensures rejected data is not confused with retained last-valid data.
        test=HERETraffic(s.graph,s.clock,transport=lambda *a:row,incidents=False,max_requests=1)
        test.service.poll_once()
        assert eid not in test.snapshot()['costs'],change
        assert test.snapshot()['live_verified'] is False
        test.close()
    now[0]+=timedelta(seconds=121)
    assert not t.snapshot()['costs']
    assert all(r['freshness_status']=='STALE' for r in t.snapshot()['observations'])
    now[0]+=timedelta(seconds=600)
    assert not t.snapshot()['costs']


def test_incident_roadclosed_and_reopen_same_stream(connected):
    s,t,now,data,_=connected
    eid=eligible_edge(s,t,now,data)
    data['incidents']=payload(s.graph,eid,now[0],incident=True,closed=True)
    t.queue.next_poll=now[0];t.service.poll_once()
    assert t.snapshot()['costs'][eid]['blocked']
    now[0]+=timedelta(seconds=1)
    data['incidents']=payload(s.graph,eid,now[0],incident=True,closed=False)
    data['incidents']['results'][0]['incidentDetails']['id']='test-incident-v2'
    t.queue.next_poll=now[0];t.service.poll_once()
    assert not t.snapshot()['costs'][eid].get('blocked')
    assert not t.snapshot()['active_closures']


def test_observed_cost_coverage_agent_and_updated_position(connected):
    s,t,now,data,_=connected
    eid=eligible_edge(s,t,now,data)
    result=s.reassess('HERE_FORMAT_FLOW')
    assert result['observed_edges']>0
    assert result['eta_provenance']['label']=='TRAFFIC_ASSISTED_ESTIMATE'
    assert 0<result['eta_provenance']['observed_fraction']<1
    assert result['eta_provenance']['source_times']==[NOW.isoformat()]
    assert result['eta_provenance']['field_validated'] is False
    assert result['agents']['traffic']['eligible_observations']>0
    new=s.graph.point_at(s.current['route'][0],.8)
    s.position(dict(source='USER_SELECTED',coordinates=new,edge=s.current['route'][0]))
    assert s.current['geometry'][0]['coordinates'][0]==s.ambulance['position']['coordinates']
    assert s.current['geometry'][0]['coordinates'][0]!=s.graph.point_at(s.current['route'][0],.5)


def test_fixture_never_live_and_retains_original_source_time(connected,tmp_path,monkeypatch):
    s,_,now,data,_=connected
    eid=s.current['route'][1]
    fixture=tmp_path/'here.json'
    fixture.write_text(json.dumps(dict(provenance='RECORDED_HERE',flow=payload(s.graph,eid,NOW),incidents=dict(results=[]))))
    monkeypatch.setenv('HERE_API_KEY','secret')
    t=HERETraffic(s.graph,s.clock,fixture=fixture,max_requests=2)
    t.service.poll_once()
    result=t.snapshot()
    assert result['source']=='REPLAY' and not result['live_verified']
    assert result['observations'][0]['observation_timestamp']==NOW.isoformat()
    assert result['accounting']['real_requests']=={'flow':0,'incidents':0}
    with pytest.raises(LiveError):t.inject(dict(condition='FLOW',edge=eid))
    t.close()


def test_session_expiry_and_endpoint_limits():
    now=[NOW]
    q=HEREQuerySession(transport=lambda *a:dict(results=[]),max_requests=4,flow_limit=1,incident_limit=1,session_seconds=60,clock=lambda:now[0])
    q.fetch(now[0]);now[0]+=timedelta(seconds=61)
    assert q.fetch(now[0]).status in {'BUDGET_EXHAUSTED','SESSION_EXPIRED'}
    assert sum(q.accounting()['attempted'].values())==2
    with pytest.raises(ValueError):HEREQuerySession(max_requests=2,flow_limit=3)
    q.close();assert q.fetch(now[0]).status=='REQUESTS_DISABLED'


def test_duplicates_do_not_create_new_cache_records(connected):
    s,t,now,data,_=connected
    eligible_edge(s,t,now,data)
    size=t.snapshot()['cache_records']
    now[0]+=timedelta(seconds=60);t.service.poll_once()
    assert t.snapshot()['cache_records']==size
    assert t.service.snapshot()['duplicates']>0


def test_provider_outage_keeps_fresh_then_estimates_after_expiry(connected):
    s,t,now,data,_=connected
    eid=eligible_edge(s,t,now,data)
    s.reassess('MEASURED')
    observed=s.current['id']
    def fail(*args):raise TimeoutError('secret')
    t.queue._transport=fail
    now[0]+=timedelta(seconds=60);t.service.poll_once()
    assert t.snapshot()['status']=='TIMEOUT'
    assert eid in t.snapshot()['costs']
    now[0]+=timedelta(seconds=61)
    with pytest.raises(LiveError,match='RECOMMENDATION_CHANGED_REVIEW_AGAIN'):
        s.transition('APPROVED',observed)
    assert s.current['observed_edges']==0
    assert 'secret' not in json.dumps(s.state(True))


def test_slow_flow_causes_route_alternative_after_stability_gate(connected):
    s,t,now,data,_=connected
    eid=eligible_edge(s,t,now,data)
    original=list(s.current['route'])
    data['flow']=payload(s.graph,eid,now[0],speed=.1)
    t.queue.next_poll=now[0];t.service.poll_once()
    kept=s.reassess('SLOW_FLOW')
    assert kept['route']==original and kept['decision']=='KEEP'
    now[0]+=timedelta(seconds=61)
    changed=s.reassess('SLOW_FLOW_AFTER_COOLDOWN')
    assert changed['decision']=='RECOMMEND_ALTERNATIVE'
    assert eid not in changed['route']
    assert changed['comparison']['improvement_seconds']>=30


def test_mocked_here_demonstration(tmp_path):
    from citybrain.live.here_demo import demonstrate
    result=demonstrate(tmp_path/'demo')
    assert result['closure']['decision']=='RECOMMEND_ALTERNATIVE'
    assert result['reopening']['decision']=='KEEP'
    assert result['initial']['route']!=result['closure']['route']
    assert result['live_verified'] is False
    assert result['real_requests']=={'flow':0,'incidents':0}


def test_mock_transport_does_not_block_snapshot_and_close_discards_late_result(connected):
    import threading,time
    s,_,now,_,_=connected
    entered,release=threading.Event(),threading.Event()
    def transport(*args):
        entered.set();release.wait(3);return dict(results=[])
    t=HERETraffic(s.graph,s.clock,transport=transport,max_requests=2)
    t.start();assert entered.wait(1)
    start=time.monotonic();snapshot=t.snapshot()
    assert time.monotonic()-start<.5
    t.close();release.set();t._worker.join(timeout=2)
    assert t.service.snapshot()['observation_count']==0
    assert snapshot['live_verified'] is False


def test_here_options_cannot_activate_in_simulation():
    import subprocess,sys
    r=subprocess.run([sys.executable,'-m','citybrain.live','--mode','simulation','--here'],capture_output=True,text=True)
    assert r.returncode!=0
    assert 'cannot be used in simulation mode' in r.stderr


def test_background_observation_updates_reassess_without_browser(connected):
    import threading
    s,old,now,data,_=connected
    eid=eligible_edge(s,old,now,data)
    data['flow']=payload(s.graph,eid,now[0],closed=True)
    old.close()
    finished=threading.Event()
    def update():
        s.reassess('HERE_OBSERVATIONS_UPDATED');finished.set()
    t=s.traffic=HERETraffic(s.graph,s.clock,transport=lambda url,*a:data[url.rsplit('/',1)[-1]],max_requests=2,on_update=update)
    t.start();assert finished.wait(2)
    assert s.current['decision']=='RECOMMEND_ALTERNATIVE'
    assert eid not in s.current['route']
    assert s.current['status']=='PENDING_OPERATOR_REVIEW'
    t.close();t._worker.join(timeout=2)
