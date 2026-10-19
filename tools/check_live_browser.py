"""Isolated offline V4 browser regression using a disposable loopback service.

Optional dependency: playwright. Uses installed Chrome; never launches SUMO or a
traffic provider. All external browser requests are blocked. No tokens are saved.
"""
import argparse
import json
from pathlib import Path
import secrets
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from citybrain.chennai.network import PILOT
from citybrain.live.service import LiveService
from citybrain.live.server import Credentials, make_server
from citybrain.live.traffic import OfflineTraffic


def main():
    from playwright.sync_api import sync_playwright, expect
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--channel', default='chrome')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    service = LiveService()
    service.traffic = OfflineTraffic(service.graph, service.clock)
    operator, hospital = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    facility = service.directory[0]['id']
    server = make_server(service, Credentials(operator, hospital, facility), 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    errors, external, http_errors = [], [], []
    report = {'source': 'SYNTHETIC_TEST', 'provider_requests': 0}
    metadata = json.loads((PILOT/'network/metadata.json').read_text())
    path = next(iter(metadata['routes'].values()))
    start, end = path[0], path[-1]

    def pick(page, point):
        page.locator('#fallback').scroll_into_view_if_needed()
        screen = page.evaluate('''p=>{const svg=document.getElementById('fallback');
            const v=svg.createSVGPoint();[v.x,v.y]=xy(p);
            const s=v.matrixTransform(svg.getScreenCTM());return {x:s.x,y:s.y};}''', point)
        box = page.locator('#fallback').bounding_box()
        page.locator('#fallback').click(position={'x':screen['x']-box['x'], 'y':screen['y']-box['y']})

    def direction(page, edge):
        # A successful unambiguous snap and an explicit direction prompt are both legal.
        page.wait_for_function("() => pendingDirection!==null || state?.ambulance!==null || state?.recommendation!==null")
        if page.locator('#direction-box').is_visible():
            page.select_option('#direction-choice', edge)
            page.click('#direction-confirm')

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=args.channel, headless=True,
                args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
            context = browser.new_context(viewport={'width': 1440, 'height': 1000})
            def boundary(route):
                if route.request.url.startswith(base+'/') or route.request.url.startswith(('data:', 'blob:')):
                    route.continue_()
                else:
                    external.append(route.request.url.split('?')[0]); route.abort()
            context.route('**/*', boundary)
            context.add_init_script("window.__qaErrors=[]; addEventListener('error', e=>window.__qaErrors.push({message:e.message, detail:e.error?.message, stack:e.error?.stack, text:String(e.error)})); addEventListener('unhandledrejection', e=>window.__qaErrors.push({type:'promise',detail:e.reason?.message,stack:e.reason?.stack,text:String(e.reason)}));")
            context.on('response', lambda response: http_errors.append({'url':response.url.replace(base,''),'status':response.status}) if response.status>=400 else None)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append({'message':str(error),'stack':error.stack}))
            page.goto(base+'/?fallback=1')
            expect(page.locator('#fallback')).to_be_visible()
            expect(page.locator('#traffic-source')).to_have_text('UNAVAILABLE')
            page.click('#report-pin')
            destination = service.graph.point_at(end, .5)
            pick(page, destination)
            # Native pointer coordinates are pixel-quantized, unlike injected exact pins.
            assert abs(float(page.input_value('#longitude'))-destination[0]) < 1e-4
            assert abs(float(page.input_value('#latitude'))-destination[1]) < 1e-4
            page.check('#confirm')
            page.locator('#report-form button[type=submit]').click()
            expect(page.locator('#notice')).to_contain_text('PENDING_VERIFICATION')
            assert service.store.rows('incidents')[0]['status'] == 'PENDING_VERIFICATION'
            page.fill('#token', operator)
            page.locator('#login-form button[type=submit]').click()
            expect(page.locator('#role')).to_have_text('OPERATOR')
            page.get_by_role('button', name='Verify for testing', exact=True).click()
            expect(page.locator('#queue')).to_contain_text('VERIFIED_FOR_TESTING')
            page.click('#ambulance-pin')
            pick(page, service.graph.point_at(start, .5))
            direction(page, start)
            expect(page.locator('#position')).to_contain_text(start)
            page.click('#recommend')
            page.wait_for_function("() => pendingDirection!==null || state?.recommendation!==null")
            if page.locator('#direction-box').is_visible():
                page.select_option('#direction-choice', end)
                page.click('#direction-confirm')
            expect(page.locator('#recommendation')).to_contain_text('RECOMMENDATION_ONLY')
            expect(page.locator('#recommendation')).to_contain_text('0 offline-observed edges')
            assert service.current['execution'] == 'RECOMMENDATION_ONLY'
            assert all(b in service.graph.next[a] for a,b in zip(service.current['route'], service.current['route'][1:]))
            assert page.locator('#fallback polyline.route').count() == len(service.current['geometry'])
            report['first_slice'] = dict(status=service.current['status'], edges=len(service.current['route']),
                estimated_edges=service.current['estimated_edges'], observed_edges=service.current['observed_edges'])
            # Choose an eligible closure with a connected alternative. These are test observations only.
            edge = None
            for candidate in service.current['route'][1:-1]:
                service.traffic.inject({'edge':candidate,'condition':'CLOSURE'})
                costs=service.traffic.snapshot()['costs']
                service.traffic.inject({'edge':candidate,'condition':'REOPEN'})
                if not costs.get(candidate,{}).get('blocked'):
                    continue
                try:
                    service.graph.route({'edge':start,'fraction':.5}, {'edge':end,'fraction':.5}, {candidate:{'blocked':True}})
                    edge=candidate; break
                except ValueError:
                    continue
            assert edge is not None
            transitions=[]
            for condition, count in [('CLOSURE',1),('REOPEN',0),('CLOSURE',1)]:
                service.traffic.inject({'edge':edge,'condition':condition})
                page.evaluate('refresh()')
                expect(page.locator('#traffic-status')).to_contain_text(f'active test closures: {count}')
                assert page.locator('#fallback polyline[stroke="#ffcf70"]').count()==count
                transitions.append(count)
            report['closure_overlays']=transitions
            service.traffic.inject({'edge':edge,'condition':'FUTURE'})
            page.evaluate('refresh()')
            expect(page.locator('#traffic-rows')).to_contain_text('FUTURE CLOCK QUARANTINED')
            assert len(service.traffic.snapshot()['active_closures'])==1
            service.traffic.inject({'edge':edge,'condition':'REOPEN'})
            page.evaluate('refresh()')
            expect(page.locator('#traffic-status')).to_contain_text('active test closures: 0')
            report['future_quarantine_and_recovery']=True
            page.screenshot(path=str(args.output/'desktop.png'), full_page=True)
            report['layouts']={}
            for width in (800,390):
                page.set_viewport_size({'width':width,'height':900})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), width
                expect(page.locator('#report-pin')).to_be_visible()
                page.screenshot(path=str(args.output/f'layout-{width}.png'),full_page=True)
                report['layouts'][str(width)]='NO_HORIZONTAL_OVERFLOW'
            page.click('#logout')
            expect(page.locator('#operator-panel')).to_be_hidden()
            page.wait_for_function('() => state?.ambulance===null && state?.recommendation===null && !token')
            assert page.evaluate('localStorage.length+sessionStorage.length')==0
            report['logout_private_state_cleared']=True
            page.fill('#token',hospital)
            page.locator('#login-form button[type=submit]').click()
            expect(page.locator('#hospital-form')).to_be_visible()
            page.select_option('#accepting','true')
            page.fill('#beds','2')
            page.locator('#hospital-form button[type=submit]').click()
            expect(page.locator('#notice')).to_contain_text('Saved STAFF_REPORTED')
            assert service.store.get('hospital',facility)['source']=='STAFF_REPORTED'
            report['hospital_portal']='FACILITY_SCOPED_STAFF_REPORTED'
            # Independent 3D capability/alignment check, with all external requests still blocked.
            scene=context.new_page()
            scene.on('pageerror', lambda error: errors.append({'message':str(error),'stack':error.stack}))
            scene.goto(base+'/')
            scene.wait_for_function('() => state!==null && (viewer!==null || useFallback)')
            report['cesium_initialized']=scene.evaluate('viewer!==null && !useFallback')
            if report['cesium_initialized']:
                geometry=scene.evaluate('''()=>{const id=Object.keys(geo.roads)[0],r=geo.roads[id];
                    const positions=viewer.entities.getById('road-'+id).polyline.positions.getValue();
                    return {expected:r.coordinates[0],actual:[Cesium.Math.toDegrees(Cesium.Cartographic.fromCartesian(positions[0]).longitude),Cesium.Math.toDegrees(Cesium.Cartographic.fromCartesian(positions[0]).latitude)]};}''')
                assert max(abs(a-b) for a,b in zip(geometry['actual'],geometry['expected']))<1e-7
                report['cesium_road_alignment']='PASS'
                scene.fill('#token',operator)
                scene.locator('#login-form button[type=submit]').click()
                expect(scene.locator('#recommendation')).to_contain_text('RECOMMENDATION_ONLY')
                agreement=scene.evaluate('''()=>{const lines=dynamic.filter(e=>e.polyline);
                    const geometry=state.recommendation.geometry;
                    let maximum=0;
                    for(let i=0;i<geometry.length;i++){
                        const points=lines[i].polyline.positions.getValue();
                        for(let j=0;j<points.length;j++){
                            const c=Cesium.Cartographic.fromCartesian(points[j]);
                            maximum=Math.max(maximum,Math.abs(Cesium.Math.toDegrees(c.longitude)-geometry[i].coordinates[j][0]),Math.abs(Cesium.Math.toDegrees(c.latitude)-geometry[i].coordinates[j][1]));
                            if(c.height<3)throw new Error('Route below display offset');
                        }
                    }
                    return maximum;}''')
                assert agreement<1e-7
                report['cesium_route_alignment']='PASS'
            else:
                report['cesium_road_alignment']='NOT_TESTED_WEBGL_UNAVAILABLE'
            # Allow asynchronous Cesium geometry workers to finish before visual evidence.
            scene.wait_for_timeout(1500)
            scene.screenshot(path=str(args.output/'cesium-or-fallback.png'))
            report['window_errors']={'scene':scene.evaluate('window.__qaErrors'),'fallback':page.evaluate('window.__qaErrors')}
            report['http_errors']=http_errors
            report['page_errors']=errors
            report['blocked_external_requests']=external
            assert not http_errors, http_errors
            assert not errors, errors
            assert not external, external
            browser.close()
    finally:
        server.shutdown(); server.server_close(); thread.join()
        service.traffic.close(); service.store.close()
        (args.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
