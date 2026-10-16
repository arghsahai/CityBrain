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
    parser.add_argument('--closure-hotfix',action='store_true',help='Verify backend closure/open/closure replacement and both marker layers')
    parser.add_argument('--keep-at',type=int,help='Verify an observed stability-deferral timestamp')
    parser.add_argument('--accepted-replan-at',type=int,help='Verify a recorded accepted replan')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(channel='chrome',headless=True,
            args=['--use-angle=gl','--enable-webgl','--ignore-gpu-blocklist'])
        page=browser.new_page(viewport={'width':1440,'height':950},device_scale_factor=1)
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
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
        page.set_viewport_size({'width':800,'height':1000})
        page.wait_for_timeout(1200)
        page.screenshot(path=str(args.output/'tablet.png'))
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
        closure_states = (assert_closure_transitions(page,
            page.request.get(args.url+'/api/state?at=220').json(),args.output) if args.closure_hotfix else [])
        assert not errors,errors
        result=dict(errors=errors,status=page.locator('#outcome').inner_text(),
            checks=['Cesium WebGL scene','moving observed ambulance','visible vehicles and both signals',
                    'accepted route geometry matches backend','actual signal states','SVG fallback',
                    'replay time filtering','terminal SUCCESS','800px layout']+
                   (['guarded KEEP and unchanged accepted P0'] if args.keep_at is not None else [])+
                   (['synthetic advisory source labels','separate external 3D and SVG flow/incident overlays','external geometry matches backend','selected road comparison','synthetic UI missing timestamp UNKNOWN and expired source label'] if args.traffic else []),
            traffic_checked=args.traffic,
            closure_states=closure_states,
            accepted_replan_checked=args.accepted_replan_at,
            browser=browser.version)
        (args.output/'browser-check.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
        browser.close()


if __name__=='__main__':
    main()
