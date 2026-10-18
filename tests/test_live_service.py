from datetime import datetime,timedelta,timezone
import json
import pytest
from citybrain.chennai.network import PILOT
from citybrain.live.graph import LiveError
from citybrain.live.service import LiveService
from citybrain.live.store import Store


@pytest.fixture
def service():
    now=[datetime(2026,10,19,tzinfo=timezone.utc)]
    s=LiveService(clock=lambda:now[0])
    s.test_clock=now
    yield s
    s.store.close()


def configured(s):
    m=json.loads((PILOT/'network/metadata.json').read_text())
    path=next(iter(m['routes'].values()))
    start,end=path[0],path[-1]
    point=s.graph.point_at(end,.5)
    incident=s.submit(dict(test=True,confirmed=True,type='ROAD_COLLISION',coordinates=point,description='<script>literal</script>'))
    s.verify(incident['id'],'VERIFIED_FOR_TESTING')
    s.position(dict(source='USER_SELECTED',coordinates=s.graph.point_at(start,.5),edge=start))
    request=dict(leg='AMBULANCE_TO_INCIDENT',incident_id=incident['id'],incident_edge=end)
    return incident,request


def test_vertical_slice_and_operator_lifecycle(service):
    incident,request=configured(service)
    r=service.recommend(request)
    assert r['status']=='PENDING_OPERATOR_REVIEW'
    assert r['execution']=='RECOMMENDATION_ONLY'
    assert r['traffic_source']=='UNAVAILABLE'
    assert r['estimated_edges']>0
    assert set(r['agents'])=={'ambulance','hospital','traffic','police','signal'}
    for state in ['APPROVED','ACKNOWLEDGED','ARRIVAL_REPORTED']:
        assert service.transition(state,service.current['id'])['status']==state
    assert service.route_request is None
    assert service.state()['incidents']==[]
    assert service.state()['recommendation'] is None


def test_verification_required_and_cancellation(service):
    incident,request=configured(service)
    service.recommend(request)
    service.verify(incident['id'],'REJECTED')
    assert service.current['status']=='CANCELLED'
    with pytest.raises(LiveError,match='VERIFIED_TEST_INCIDENT_REQUIRED'):
        service.recommend(request)
    with pytest.raises(LiveError,match='INVALID_INCIDENT_TRANSITION'):
        service.verify(incident['id'],'VERIFIED_FOR_TESTING')


def test_validation_duplicate_and_no_gps(service):
    incident,request=configured(service)
    row=service.store.get('incidents',incident['id'])
    with pytest.raises(LiveError,match='POSSIBLE_DUPLICATE'):
        service.submit(dict(test=True,confirmed=True,type=row['type'],coordinates=row['coordinates']))
    with pytest.raises(LiveError,match='TEST_AND_LOCATION_CONFIRMATION_REQUIRED'):
        service.submit({})
    with pytest.raises(LiveError,match='AUTHORIZED_GPS_NOT_IMPLEMENTED'):
        service.position(dict(source='AUTHORIZED_GPS',coordinates=row['coordinates']))
    with pytest.raises(LiveError,match='INVALID_TEXT'):
        service.submit(dict(test=True,confirmed=True,type='OTHER_TEST',coordinates=row['coordinates'],description='x'*301))


def test_position_changes_reassess_current_position(service):
    _,request=configured(service)
    first=service.recommend(request)
    service.transition('APPROVED',service.current['id'])
    edge=first['route'][2]
    service.position(dict(source='USER_SELECTED',coordinates=service.graph.point_at(edge,.4),edge=edge))
    assert service.current['route'][0]==edge
    assert service.current['status']=='PENDING_OPERATOR_REVIEW'
    assert service.current['id']!=first['id']


def test_hospital_unknown_expiry_validation_and_second_leg(service):
    incident,request=configured(service)
    assert all(h['availability']=='AVAILABILITY_UNKNOWN' for h in service.hospitals())
    with pytest.raises(LiveError,match='INCIDENT_ARRIVAL_CONFIRMATION_REQUIRED'):
        service.recommend(dict(request,leg='INCIDENT_TO_HOSPITAL'))
    with pytest.raises(LiveError,match='CURRENT_POSITION_NOT_AT_INCIDENT'):
        service.recommend(dict(request,leg='INCIDENT_TO_HOSPITAL',incident_arrival_confirmed=True))
    edge=request['incident_edge']
    service.position(dict(source='USER_SELECTED',coordinates=service.graph.point_at(edge,.5),edge=edge))
    second=dict(request,leg='INCIDENT_TO_HOSPITAL',incident_arrival_confirmed=True,require_icu=True)
    with pytest.raises(LiveError,match='NO_RECENT_SUITABLE_REACHABLE_HOSPITAL'):
        service.recommend(second)
    key=service.directory[0]['id']
    with pytest.raises(LiveError,match='INVALID_BED_COUNT'):
        service.hospital_update(key,dict(beds=-1),'facility')
    service.hospital_update(key,dict(accepting=True,icu=True,beds=2),'facility')
    r=service.recommend(second)
    assert r['hospital']['id']==key
    assert r['hospital']['status']['source']=='STAFF_REPORTED'
    service.hospital_update(key,dict(accepting=False),'facility')
    assert service.current['status']=='UNAVAILABLE'
    service.hospital_update(key,dict(accepting=True,icu=True,beds=2),'facility')
    assert service.current['status']=='PENDING_OPERATOR_REVIEW'
    service.test_clock[0]+=timedelta(seconds=901)
    assert service.state(True)['recommendation']['status']=='UNAVAILABLE'
    assert service.hospitals()[0]['availability']=='AVAILABILITY_UNKNOWN'


def test_retention_limits_and_deletion(tmp_path):
    p=tmp_path/'private'/'live.sqlite'
    store=Store(str(p))
    for i in range(20):
        store.put('audit',str(i),dict(id=i),i,limit=5)
    assert len(store.rows('audit'))==5
    assert p.stat().st_mode & 0o777 == 0o600
    store.delete('audit','19')
    assert store.get('audit','19') is None
    store.prune(90000)
    assert store.rows('audit')==[]
    store.close()


def test_unknown_beds_cannot_become_hospital_capacity(service):
    incident,request=configured(service)
    edge=request['incident_edge']
    service.position(dict(source='USER_SELECTED',coordinates=service.graph.point_at(edge,.5),edge=edge))
    service.hospital_update(service.directory[0]['id'],dict(accepting=True,icu=True),'facility')
    with pytest.raises(LiveError,match='NO_RECENT_SUITABLE_REACHABLE_HOSPITAL'):
        service.recommend(dict(request,leg='INCIDENT_TO_HOSPITAL',incident_arrival_confirmed=True))


def test_reassessment_history_deduplicates_polling(service):
    _,request=configured(service)
    service.recommend(request)
    for _ in range(100):
        service.state(True)
    assert len(service.history)==2
    assert service.history[0]['action']=='RECOMMENDED'


def test_agent_sources_do_not_claim_unavailable_traffic_or_capacity(service):
    _,request=configured(service)
    agents=service.recommend(request)['agents']
    assert agents['traffic']['source']=='UNAVAILABLE'
    assert agents['traffic']['source_updated_at']==[]
    assert agents['ambulance']['source']=='USER_SELECTED'
    assert agents['hospital']['source']=='UNAVAILABLE'
    assert agents['hospital']['source_updated_at'] is None
    assert agents['signal']['source_updated_at'] is None
    assert all(a['assessment_at'] for a in agents.values())
