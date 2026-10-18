"""Optional browser QA. Install playwright; requires Chrome or its Chromium build."""
import argparse
import json
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright, expect


def assert_closure_transitions(page, state, output):
    """Synthetic backend-to-renderer regression; never issues provider requests."""
    from copy import deepcopy
    from dataclasses import replace
    from datetime import timedelta
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from citybrain.chennai.network import PILOT, read_network
    from citybrain.chennai.traffic import ReplayTrafficProvider
    from citybrain.chennai.traffic.matching import RoadMatcher
    from citybrain.chennai.traffic.provider import FetchResult
    from citybrain.chennai.traffic.service import TrafficService

    sample = ReplayTrafficProvider(PILOT/'scenarios/traffic-sample-v22.json').records[0]
    clock = [sample.observation_timestamp]
    class SyntheticProvider:
        name = 'REPLAY'
        rows = []
        def fetch(self, now):
            return FetchResult(self.rows,'REPLAY')
    provider = SyntheticProvider()
    service = TrafficService(provider,RoadMatcher(read_network()),clock=lambda:clock[0])
    observed = []
    for index,incident in enumerate(('ROAD_CLOSURE',None,'ROAD_CLOSURE')):
        clock[0] = sample.observation_timestamp+timedelta(seconds=30*index)
        provider.rows = [replace(sample,observation_id='closure-state-'+str(index),
            observation_timestamp=clock[0],retrieved_at=clock[0],incident_type=incident,
            incident_description='Synthetic hotfix browser regression' if incident else None)]
        service.poll_once()
        if incident is None:
            provider.rows = [replace(sample,observation_id='late-closure',
                observation_timestamp=clock[0]-timedelta(seconds=1),incident_type='ROAD_CLOSURE')]
            service.poll_once()  # An older closure must not resurrect the marker.
        frame = deepcopy(state)
        frame['chennai']['external'] = service.snapshot()
        assert len(frame['chennai']['external']['observations']) == 1
        rendered = page.evaluate('''state=>{
            playing=false;renderTrafficPanel(state);renderTrafficOverlay(state.chennai);renderFallback(state);
            return {markers:[...externalEntities.keys()].filter(id=>id.startsWith('external-incident:')).length,
                svgMarkers:[...document.querySelectorAll('#fallback text')].filter(e=>e.textContent.includes('ROAD_CLOSURE')).length};
        }''',frame)
        expected = 1 if incident else 0
        assert rendered == dict(markers=expected,svgMarkers=expected),rendered
        expect(page.locator('#traffic-status')).to_contain_text('SYNTHETIC_SAMPLE')
        expect(page.locator('#traffic-comparison')).to_contain_text('MATCHED')
        observed.append(dict(state=incident or 'OPEN',**rendered))
        if incident is None:
            page.locator('#traffic-panel').scroll_into_view_if_needed()
            page.screenshot(path=str(output/'reopening.png'))
    # A bad source clock must not replace the current closure or block a later
    # valid reopening. Diagnostics are visible, but the invalid row is not drawn.
    provider.rows = [replace(sample,observation_id='future-clock',
        observation_timestamp=clock[0]+timedelta(days=365),incident_type=None)]
    service.poll_once()
    assert service.snapshot()['observations'][0]['observation_id'] == 'closure-state-2'
    assert service.snapshot()['quarantine_count'] == 1
    frame['chennai']['external'] = service.snapshot()
    page.evaluate('(state)=>{renderTrafficPanel(state);renderTrafficOverlay(state.chennai);}',frame)
    expect(page.locator('#traffic-errors')).to_contain_text('Quarantined future timestamps: 1')
    assert page.evaluate("[...externalEntities.keys()].filter(id=>id.startsWith('external-incident:')).length") == 1
    clock[0] += timedelta(seconds=30)
    provider.rows = [replace(sample,observation_id='clock-recovered',
        observation_timestamp=clock[0],incident_type=None,incident_description=None)]
    service.poll_once()
    assert service.snapshot()['observations'][0]['observation_id'] == 'clock-recovered'
    frame['chennai']['external'] = service.snapshot()
    page.evaluate('(state)=>{renderTrafficPanel(state);renderTrafficOverlay(state.chennai);renderFallback(state);}',frame)
    assert page.evaluate("[...externalEntities.keys()].filter(id=>id.startsWith('external-incident:')).length") == 0
    assert page.locator('#fallback text').filter(has_text='ROAD_CLOSURE').count() == 0
    observed.append(dict(state='FUTURE_CLOCK_QUARANTINED_AND_RECOVERED',markers=0,svgMarkers=0))
    return observed


def assert_rendered_route(page,state,geography):
    expected=[point for edge in state['plan']['route'] for point in geography['roads'][edge]['coordinates']]
    rendered=page.evaluate('routeEntity.polyline.positions.getValue(viewer.clock.currentTime).map(p=>{const c=Cesium.Cartographic.fromCartesian(p);return [Cesium.Math.toDegrees(c.longitude),Cesium.Math.toDegrees(c.latitude)];})')
    assert len(rendered)==len(expected)
    assert all(abs(a-b)<1e-7 for actual,wanted in zip(rendered,expected) for a,b in zip(actual,wanted))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8770')
    parser.add_argument('--output',type=Path,default=Path('docs/chennai'))
    parser.add_argument('--traffic',action='store_true',help='Verify synthetic advisory panel and 3D/2D overlays')
    parser.add_argument('--experimental-advisor',action='store_true',help='Render a mocked, display-only route recommendation')
    parser.add_argument('--closure-hotfix',action='store_true',help='Verify backend closure/open/closure replacement and both marker layers')
    parser.add_argument('--keep-at',type=int,help='Verify an observed stability-deferral timestamp')
    parser.add_argument('--accepted-replan-at',type=int,help='Verify a recorded accepted replan')
    parser.add_argument('--device-location',action='store_true',help='Emulate one explicitly consented, local browser location fix')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(channel='chrome',headless=True,
            args=['--use-angle=gl','--enable-webgl','--ignore-gpu-blocklist'])
        page=browser.new_page(viewport={'width':1440,'height':950},device_scale_factor=1)
        if args.device_location:
            # Emulate a consented browser location source without reading the
            # reviewer's actual device coordinates or contacting a service.
            page.add_init_script("""Object.defineProperty(navigator,'geolocation',{configurable:true,value:{watchPosition:(ok,fail)=>{window.__gpsOk=ok;window.__gpsFail=fail;return 7;},clearWatch:()=>{window.__gpsCleared=true;}}});""")
        errors=[]
        local_http_errors=[]
        location_scenarios=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('response',lambda response:local_http_errors.append(dict(url=response.url,status=response.status))
                if response.url.startswith(args.url) and response.status>=400 else None)
        page.goto(args.url,wait_until='domcontentloaded')
        expect(page.locator('#mode')).to_contain_text('REPLAY',timeout=60000)
        terminal_time=page.request.get(args.url+'/api/state').json()['telemetry_max_time']
        if args.keep_at is not None:
            page.locator('#seek').fill(str(args.keep_at))
            page.locator('#seek').dispatch_event('input')
            expect(page.locator('#time')).to_have_text(f'{args.keep_at} s',timeout=30000)
            expect(page.locator('#decision')).to_have_text('KEEP')
            expect(page.locator('#reason')).to_have_text('soft_change_confirmation_pending')
            state=page.request.get(args.url+f'/api/state?at={args.keep_at}').json()
            assert state['decision']['decision']=='KEEP'
            assert state['plan']['revision']==0
            page.screenshot(path=str(args.output/'keep.png'))
        page.locator('#seek').fill('200')
        page.locator('#seek').dispatch_event('input')
        expect(page.locator('#time')).to_have_text('200 s',timeout=30000)
        expect(page.locator('#play')).to_have_text('Play replay')
        expect(page.locator('header')).not_to_contain_text('V3.0')
        page.wait_for_timeout(1500)
        assert not page.locator('#fallback').is_visible(),page.locator('#notice').inner_text()
        assert page.evaluate('Boolean(viewer && viewer.scene.canvas && !fallbackMode)')
        assert page.evaluate('vehicles.size')>10
        assert page.evaluate('signals.size')==2
        assert page.evaluate('routeEntity.polyline.positions.getValue(viewer.clock.currentTime).length')>2
        state=page.request.get(args.url+'/api/state?at=200').json()
        geography=page.request.get(args.url+'/api/geography').json()
        assert_rendered_route(page,state,geography)
        for signal in state['chennai']['signals']:
            assert signal['state'] in page.locator('#signals').inner_text()
        if args.device_location:
            candidate=page.evaluate('''()=>{for(const road of Object.values(geo.roads)){const p=road.coordinates;for(let i=1;i<p.length;i++){const a=p[i-1],b=p[i],point=t=>({longitude:a[0]+(b[0]-a[0])*t,latitude:a[1]+(b[1]-a[1])*t}),x=point(.4),y=point(.6),mx=matchDevicePoint(x.longitude,x.latitude),my=matchDevicePoint(y.longitude,y.latitude);if(mx.status==='MATCHED'&&my.status==='MATCHED'&&mx.road===my.road)return {...x,next:y,road:mx.road};}}return null;}''')
            assert candidate, 'No unambiguous road point available for the browser location fixture'
            page.get_by_text('Consented device location (local display only)',exact=False).click()
            page.locator('#location-start').click()
            def deliver(lon,lat,*,accuracy=8,timestamp=None,speed=0):
                page.evaluate('''f=>window.__gpsOk({timestamp:f.timestamp ?? Date.now(),coords:{longitude:f.longitude,latitude:f.latitude,accuracy:f.accuracy,speed:f.speed}})''',
                    dict(longitude=lon,latitude=lat,accuracy=accuracy,speed=speed,timestamp=timestamp))
            test_time=__import__('time').time()*1000-20000
            deliver(candidate['longitude'],candidate['latitude'],timestamp=test_time)
            expect(page.locator('#location-status')).to_contain_text('STALE',timeout=10000)
            deliver(candidate['longitude'],candidate['latitude'],timestamp=test_time+16000)
            expect(page.locator('#location-status')).to_contain_text('CONSENTED DEVICE · LOCAL TAB ONLY · MATCHED',timeout=10000)
            assert page.evaluate("Boolean(viewer.entities.getById('consented-device-location') && viewer.entities.getById('consented-device-accuracy'))")
            expect(page.locator('#location-status')).to_contain_text(candidate['road'])
            deliver(candidate['next']['longitude'],candidate['next']['latitude'],timestamp=test_time+17000,speed=2)
            expect(page.locator('#location-status')).to_contain_text(candidate['road'])
            location_scenarios.append('accurate movement')
            deliver(candidate['next']['longitude'],candidate['next']['latitude'],timestamp=test_time+16500)
            expect(page.locator('#location-status')).to_contain_text('out-of-order location')
            deliver(candidate['longitude'],candidate['latitude'],timestamp=test_time+17500)
            deliver(candidate['next']['longitude'],candidate['next']['latitude'],accuracy=100,timestamp=test_time+18000)
            expect(page.locator('#location-status')).to_contain_text('FIX REJECTED · accuracy',timeout=10000)
            assert page.evaluate("!viewer.entities.getById('consented-device-location')")
            deliver(candidate['longitude'],candidate['latitude'],timestamp=test_time+19000)
            expect(page.locator('#location-status')).to_contain_text(candidate['road'])
            location_scenarios += ['stale fix','poor accuracy rejection','out-of-order rejection']
            deliver(candidate['longitude']+.01,candidate['latitude'],timestamp=test_time+20000)
            expect(page.locator('#location-status')).to_contain_text('impossible position jump',timeout=10000)
            page.evaluate("window.__gpsFail({code:2})")
            expect(page.locator('#location-status')).to_contain_text('position unavailable',timeout=10000)
            deliver(candidate['longitude'],candidate['latitude'],timestamp=test_time+21000)
            expect(page.locator('#location-status')).to_contain_text(candidate['road'])
            location_scenarios += ['impossible jump rejection','dropout and recovery']
            ambiguous=page.evaluate('''()=>{for(const road of Object.values(geo.roads))for(let i=1;i<road.coordinates.length;i++){const a=road.coordinates[i-1],b=road.coordinates[i],longitude=(a[0]+b[0])/2,latitude=(a[1]+b[1])/2;if(matchDevicePoint(longitude,latitude).status==='AMBIGUOUS')return {longitude,latitude};}return null;}''')
            assert ambiguous, 'The Chennai road geometry did not provide an ambiguity fixture'
            deliver(ambiguous['longitude'],ambiguous['latitude'],timestamp=test_time+22000)
            expect(page.locator('#location-status')).to_contain_text('AMBIGUOUS')
            location_scenarios.append('parallel-road ambiguity')
            page.locator('#location-stop').click()
            expect(page.locator('#location-status')).to_have_text('DEVICE LOCATION OFF')
            assert page.evaluate("!viewer.entities.getById('consented-device-location') && window.__gpsCleared===true")
            location_scenarios.append('stop clears marker')
        if args.traffic:
            expect(page.locator('#traffic-status')).to_contain_text('SYNTHETIC_SAMPLE')
            expect(page.locator('#traffic-status')).to_contain_text('REPLAY')
            expect(page.locator('#traffic-comparison')).to_contain_text('sample-segment')
            expect(page.locator('#traffic-comparison')).to_contain_text('SUMO_SIMULATED')
            observations=state['chennai']['external']['observations']
            assert observations and observations[0]['matching_status']=='MATCHED'
            assert page.evaluate("[...externalEntities.keys()].some(id=>id.startsWith('external-flow:'))")
            assert page.evaluate("[...externalEntities.keys()].some(id=>id.startsWith('external-incident:'))")
            rendered=page.evaluate("[...externalEntities.values()].find(e=>e.polyline).polyline.positions.getValue(viewer.clock.currentTime).map(p=>{const c=Cesium.Cartographic.fromCartesian(p);return [Cesium.Math.toDegrees(c.longitude),Cesium.Math.toDegrees(c.latitude)];})")
            expected=observations[0]['road_geometry']
            assert len(rendered)==len(expected)
            assert all(abs(a-b)<1e-7 for actual,wanted in zip(rendered,expected) for a,b in zip(actual,wanted))
            page.locator('#traffic-panel').scroll_into_view_if_needed()
            page.screenshot(path=str(args.output/'traffic.png'))
        first=page.locator('#ambulance').inner_text()
        page.screenshot(path=str(args.output/'desktop.png'))
        page.locator('#seek').fill('220')
        page.locator('#seek').dispatch_event('input')
        expect(page.locator('#time')).to_have_text('220 s',timeout=30000)
        assert page.locator('#ambulance').inner_text()!=first
        if args.accepted_replan_at is not None:
            at=args.accepted_replan_at
            page.locator('#seek').fill(str(at))
            page.locator('#seek').dispatch_event('input')
            expect(page.locator('#time')).to_have_text(f'{at} s',timeout=30000)
            state=page.request.get(args.url+f'/api/state?at={at}').json()
            assert len(state['plans'])>=2
            expect(page.locator('#replans')).to_have_text(str(len(state['plans'])))
            assert state['execution']['verification']=='VERIFIED'
            assert state['execution']['intended_suffix']==state['plan']['route']
            assert_rendered_route(page,state,geography)
            page.wait_for_timeout(1500)
            page.screenshot(path=str(args.output/'replan.png'))
        page.locator('#flat').click()
        assert page.locator('#fallback').is_visible()
        assert page.locator('#fallback polyline').count()>700
        if args.traffic:
            assert page.locator('#fallback polyline[stroke="#d48cfa"], #fallback polyline[stroke="#9ca6b4"]').count()>0
        page.screenshot(path=str(args.output/'fallback.png'))
        page.locator('#seek').fill(f'{terminal_time:g}')
        page.locator('#seek').dispatch_event('input')
        expect(page.locator('#outcome')).to_contain_text('SUCCESS',timeout=30000)
        expect(page.locator('#terminal-vehicle')).to_contain_text('No active SUMO vehicle')
        expect(page.locator('#follow')).to_be_disabled()
        expect(page.locator('#ambulance')).to_contain_text('Travel time')
        expect(page.locator('#play')).to_have_text('Play replay')
        page.set_viewport_size({'width':800,'height':1000})
        page.wait_for_timeout(1200)
        page.screenshot(path=str(args.output/'tablet.png'))
        page.set_viewport_size({'width':390,'height':844})
        page.wait_for_timeout(500)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'), '390px horizontal overflow'
        page.screenshot(path=str(args.output/'phone.png'))
        if args.traffic:
            # Presentation-only synthetic UI cases; not provider/API evidence.
            frame=page.request.get(args.url+'/api/state?at=220').json()
            sample=frame['chennai']['external']['observations'][0]
            sample.update(observation_timestamp=None,age_seconds=None,freshness_status='UNKNOWN')
            frame['chennai']['external']['unknown_time_records']=1
            page.evaluate('(state)=>renderTrafficPanel(state)',frame)
            expect(page.locator('#traffic-comparison')).to_contain_text('UNKNOWN')
            expect(page.locator('#traffic-time')).to_contain_text('Source age: UNKNOWN')
            sample.update(observation_timestamp='2026-10-16T00:00:00+00:00',age_seconds=700,freshness_status='EXPIRED')
            frame['chennai']['external'].update(stale_records=1,unknown_time_records=0)
            page.evaluate('(state)=>renderTrafficPanel(state)',frame)
            expect(page.locator('#traffic-comparison')).to_contain_text('EXPIRED')
        if args.experimental_advisor:
            from copy import deepcopy
            frame=deepcopy(state)
            frame['chennai']['external']['experimental_evaluation']={
                'enabled':True,'action':'ADVISORY_RECOMMENDATION','candidate':'candidate-b',
                'reason':'ELIGIBLE_EXPERIMENTAL_EVIDENCE','score_basis':'SUMO_FREE_FLOW_LENGTH_OVER_SPEED',
                'baseline_scores':{'current':40,'candidate-b':25},
                'adjusted_scores':{'current':40,'candidate-b':31},'evidence_used':['fixture-1'],
                'candidate_rejections':{'candidate-c':'DISCONNECTED_ROUTE'},
                'evidence':[{'observation_id':'fixture-1','provenance':'MOCKED_PROVIDER','freshness':'FRESH'}]}
            page.evaluate('(value)=>renderTrafficPanel(value)',frame)
            expect(page.locator('#experimental-advisor')).to_contain_text('ADVISORY_RECOMMENDATION')
            expect(page.locator('#experimental-advisor')).to_contain_text('DISPLAY ONLY')
            expect(page.locator('#experimental-evidence')).to_contain_text('MOCKED_PROVIDER')
            expect(page.locator('#experimental-evidence')).to_contain_text('DISCONNECTED_ROUTE')
        closure_states = (assert_closure_transitions(page,
            page.request.get(args.url+'/api/state?at=220').json(),args.output) if args.closure_hotfix else [])
        assert not errors,errors
        assert not local_http_errors,local_http_errors
        result=dict(errors=errors,status=page.locator('#outcome').inner_text(),
            local_http_errors=local_http_errors,
            checks=['Cesium WebGL scene','moving observed ambulance','visible vehicles and both signals',
                    'accepted route geometry matches backend','actual signal states','SVG fallback',
                    'replay time filtering','terminal SUCCESS','800px layout']+
                   (['guarded KEEP and unchanged accepted P0'] if args.keep_at is not None else [])+
                   (['synthetic advisory source labels','separate external 3D and SVG flow/incident overlays','external geometry matches backend','selected road comparison','synthetic UI missing timestamp UNKNOWN and expired source label'] if args.traffic else [])+
                   (['mocked experimental candidate evidence rendered as display-only'] if args.experimental_advisor else []),
            traffic_checked=args.traffic,
            experimental_advisor_checked=args.experimental_advisor,
            consented_device_location_checked=args.device_location,
            consented_location_scenarios=location_scenarios,
            closure_states=closure_states,
            accepted_replan_checked=args.accepted_replan_at,
            browser=browser.version)
        (args.output/'browser-check.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
        browser.close()


if __name__=='__main__':
    main()
