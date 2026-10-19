import json
import threading
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import pytest
from citybrain.live.service import LiveService
from citybrain.live.server import Credentials,make_server

OP='o'*40
HOSP='h'*40


@pytest.fixture
def api():
    s=LiveService()
    facility=s.directory[0]['id']
    server=make_server(s,Credentials(OP,HOSP,facility),port=0)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    def call(path,body=None,token=None,headers=None):
        hdr={'Content-Type':'application/json'}
        if token:
            hdr['Authorization']='Bearer '+token
        hdr.update(headers or {})
        req=Request(f'http://127.0.0.1:{server.server_port}/api/live/'+path,
                    data=json.dumps(body).encode() if body is not None else None,headers=hdr)
        try:
            response=urlopen(req,timeout=3)
        except HTTPError as error:
            response=error
        return response.code,json.loads(response.read())
    call.base=f'http://127.0.0.1:{server.server_port}'
    yield call,s,facility
    server.shutdown(); server.server_close(); thread.join(); s.store.close()


def test_roles_and_origin(api):
    call,s,facility=api
    assert call('session')[0]==401
    assert call('session',token=OP)[1]['role']=='operator'
    assert call('session',token=HOSP)[1]['facility']==facility
    assert call('position',{},HOSP)[0]==403
    assert call('verify',{})[0]==401
    assert call('state',headers={'Host':'evil.example'})[0]==403
    assert call('incidents',{},headers={'Origin':'https://evil.example'})[0]==400
    assert call('state',token='wrong')[0]==401
    assert call('hospital',dict(hospital_id=facility,accepting=True),OP)[0]==403
    assert call('hospital',dict(hospital_id='other',accepting=True),HOSP)[0]==403
    assert call('hospital',dict(hospital_id=facility,accepting=True,beds=2),HOSP)[0]==200


def test_public_submission_auth_queue_and_limits(api):
    call,s,_=api
    eid=next(iter(s.graph.edges))
    body=dict(test=True,confirmed=True,type='ROAD_COLLISION',coordinates=s.graph.point_at(eid,.5))
    status,row=call('incidents',body)
    assert status==201 and row['status']=='PENDING_VERIFICATION'
    assert call('state')[1]['incidents']==[]
    assert len(call('state',token=OP)[1]['incidents'])==1
    assert call('verify',dict(id=row['id'],status='VERIFIED_FOR_TESTING'),OP)[0]==200
    assert call('incidents',body)[1]['error']=='POSSIBLE_DUPLICATE'
    for _ in range(5):
        last=call('incidents',body)
    assert last[0]==429


def test_validation_size_and_secret_safety(api):
    call,s,_=api
    assert call('incidents',{'description':'x'*17000})[0]==413
    assert call('position',dict(source='USER_SELECTED',coordinates=[80,float('nan')]),OP)[0]==400
    assert call('position',{},OP)[1]['error']=='AUTHORIZED_GPS_NOT_IMPLEMENTED'
    assert OP not in json.dumps(call('state',token=OP)[1])
    assert call('incidents',{},headers={'Content-Type':'text/plain'})[0]==415
    for _ in range(11):
        last=call('verify',{},token='wrong')
    assert last[0]==429


def test_credential_configuration():
    with pytest.raises(ValueError):
        Credentials('short')
    with pytest.raises(ValueError):
        Credentials(OP,OP,'facility')
    with pytest.raises(ValueError):
        Credentials(OP,HOSP)


@pytest.mark.parametrize('asset', [
    'Assets/approximateTerrainHeights.json',
    'Assets/IAU2006_XYS/IAU2006_XYS_18.json',
])
def test_cesium_static_json_is_served_without_reserialization(api, asset):
    from citybrain.chennai.network import ROOT
    call, _, _ = api
    expected = (ROOT/'dashboard/cesium/vendor/Cesium'/asset).read_bytes()
    with urlopen(call.base+'/vendor/Cesium/'+asset, timeout=3) as response:
        assert response.status == 200
        assert response.headers.get_content_type() == 'application/json'
        payload = response.read()
    assert payload == expected
    assert isinstance(json.loads(payload), dict)
