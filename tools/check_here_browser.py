"""Offline HERE-format dashboard smoke. Disposable local state; no API requests."""
import argparse
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import secrets
import sys
import threading

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from citybrain.live.here import HERETraffic
from citybrain.live.here_demo import flow_payload
from citybrain.live.service import LiveService
from citybrain.live.server import Credentials,make_server
from citybrain.chennai.network import PILOT


def main():
    from playwright.sync_api import sync_playwright,expect
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    now=[datetime.now(timezone.utc)]
    service=LiveService(clock=lambda:now[0])
    frames={k:dict(sourceUpdated=now[0].isoformat(),results=[]) for k in ('flow','incidents')}
    service.traffic=HERETraffic(service.graph,service.clock,max_requests=20,
        transport=lambda url,*_:frames[url.rsplit('/',1)[-1]])
    operator=secrets.token_urlsafe(32)
    server=make_server(service,Credentials(operator),0)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    report={'source':'REPLAY','provider_requests':0}
    errors=[]
    try:
        path=next(iter(json.loads((PILOT/'network/metadata.json').read_text())['routes'].values()))
        row=service.submit(dict(test=True,confirmed=True,type='ROAD_COLLISION',coordinates=service.graph.point_at(path[-1],.5)))
        service.verify(row['id'],'VERIFIED_FOR_TESTING')
        service.position(dict(source='USER_SELECTED',edge=path[0],coordinates=service.graph.point_at(path[0],.5)))
        service.recommend(dict(leg='AMBULANCE_TO_INCIDENT',incident_id=row['id'],incident_edge=path[-1]))
        edge='-828326390#4'
        assert edge in service.current['route']
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='chrome',headless=True)
            context=browser.new_context(viewport={'width':1440,'height':1000})
            external=[]
            def boundary(route):
                if route.request.url.startswith(base+'/'):
                    route.continue_()
                else:
                    external.append(route.request.url.split('?')[0]);route.abort()
            context.route('**/*',boundary)
            page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(base+'/?fallback=1')
            page.fill('#token',operator);page.locator('#login-form button[type=submit]').click()
            expect(page.locator('#role')).to_have_text('OPERATOR')
            frames['flow']=flow_payload(service.graph,edge,now[0],speed=2)
            service.traffic.service.poll_once();page.evaluate('refresh()')
            expect(page.locator('#traffic-source')).to_have_text('REPLAY')
            expect(page.locator('#traffic-rows')).to_contain_text('Speed: 2 m/s')
            expect(page.locator('#traffic-status')).to_contain_text('HERE: REPLAY')
            expect(page.locator('#recommendation')).to_contain_text('TRAFFIC_ASSISTED_ESTIMATE')
            expect(page.locator('#traffic-test-panel')).to_be_hidden()
            original=list(service.current['route'])
            counts=[]
            for closed,count in [(True,1),(False,0),(True,1)]:
                now[0]+=timedelta(seconds=1)
                frames['flow']=flow_payload(service.graph,edge,now[0],closed=closed)
                service.traffic.queue.next_poll=now[0];service.traffic.service.poll_once()
                page.evaluate('refresh()')
                expect(page.locator('#traffic-status')).to_contain_text(f'active closures: {count}')
                assert page.locator('#fallback polyline[stroke="#ffcf70"]').count()==count
                counts.append(count)
            assert service.current['route']!=original and edge not in service.current['route']
            expect(page.locator('#recommendation')).to_contain_text('RECOMMENDATION_ONLY')
            page.locator('#recommendation').scroll_into_view_if_needed()
            page.screenshot(path=str(args.output/'here-replay.png'),full_page=True)
            report.update(closure_overlays=counts,alternative_edges=len(service.current['route']),
                decision=service.current['decision'],comparison=service.current['comparison'],
                page_errors=errors,external_requests=external,accounting=service.traffic.queue.accounting())
            assert not errors and not external
            assert not any(report['accounting']['real_requests'].values())
            browser.close()
    finally:
        server.shutdown();server.server_close();thread.join()
        service.traffic.close();service.store.close()
        (args.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
