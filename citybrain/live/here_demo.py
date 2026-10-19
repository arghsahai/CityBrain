"""Deterministic offline HERE-format routing demo. No provider credentials or I/O.

Writes explicit MOCKED_HERE fixtures and a compact route/cost report. All geometry
comes from the retained pilot; conditions are invented test observations.
"""
from copy import deepcopy
import argparse
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
from citybrain.chennai.network import PILOT
from .graph import LiveError
from .service import LiveService
from .here import HERETraffic


def flow_payload(graph,edge,at,*,closed=False,speed=13):
    return dict(sourceUpdated=at.isoformat(),results=[dict(
        location=dict(shape=dict(links=[dict(points=[dict(lng=p[0],lat=p[1]) for p in graph.edges[edge]['coordinates']])])),
        currentFlow=dict(speed=speed,freeFlow=13,jamFactor=10 if closed else 1,confidence=.99,
                         traversability='closed' if closed else 'open'))])


def demonstrate(output=None):
    now=[datetime.now(timezone.utc)]
    service=LiveService(clock=lambda:now[0])
    frames={kind:dict(sourceUpdated=now[0].isoformat(),results=[]) for kind in ('flow','incidents')}
    traffic=service.traffic=HERETraffic(service.graph,service.clock,max_requests=100,
        transport=lambda url,*_:frames[url.rsplit('/',1)[-1]])
    try:
        path=next(iter(json.loads((PILOT/'network/metadata.json').read_text())['routes'].values()))
        incident=service.submit(dict(test=True,confirmed=True,type='ROAD_COLLISION',
            coordinates=service.graph.point_at(path[-1],.5),description='MOCKED HERE demo; no actual incident'))
        service.verify(incident['id'],'VERIFIED_FOR_TESTING')
        service.position(dict(source='USER_SELECTED',coordinates=service.graph.point_at(path[0],.5),edge=path[0]))
        request=dict(leg='AMBULANCE_TO_INCIDENT',incident_id=incident['id'],incident_edge=path[-1])
        initial=service.recommend(request)
        original=list(initial['route'])
        selected=None
        for edge in original[1:-1]:
            frames['flow']=flow_payload(service.graph,edge,now[0],closed=True)
            traffic.queue.next_poll=now[0];traffic.service.poll_once()
            if not traffic.snapshot()['costs'].get(edge,{}).get('blocked'):
                continue
            try:
                candidate=service._compute(request)
            except LiveError:
                continue
            if edge not in candidate['route']:
                selected=edge;break
        if selected is None:
            raise AssertionError('No conservatively matched closure diversion')
        closed_fixture=dict(provenance='MOCKED_HERE',**frames)
        # Copy before subsequent mutation; the public result contains no credentials or raw reports.
        changed=deepcopy(service.reassess('MOCKED_HERE_CLOSURE'))
        assert changed['decision']=='RECOMMEND_ALTERNATIVE'
        alternative=list(changed['route'])
        assert original!=alternative and selected not in alternative
        now[0]+=timedelta(seconds=1)
        frames['flow']=flow_payload(service.graph,selected,now[0])
        traffic.queue.next_poll=now[0];traffic.service.poll_once()
        kept=deepcopy(service.reassess('MOCKED_HERE_REOPEN'))
        assert kept['route']==alternative and kept['decision']=='KEEP'
        now[0]+=timedelta(seconds=60)
        # Reopening after cooldown can restore the estimated baseline if it is sufficiently better.
        refreshed=service.reassess('MOCKED_HERE_COOLDOWN_COMPLETE')
        report=dict(source='REPLAY',fixture_provenance='MOCKED_HERE',live_verified=False,
            real_requests=traffic.queue.accounting()['real_requests'],edge=selected,
            initial=dict(route=original,eta_seconds=initial['eta_seconds'],eta_provenance=initial['eta_provenance']),
            closure=dict(route=alternative,decision=changed['decision'],reason=changed['reason'],
                comparison=changed['comparison'],status=changed['status']),
            reopening=dict(route=list(kept['route']),decision='KEEP',reason=kept['reason']),
            after_cooldown=dict(route=refreshed['route'],decision=refreshed['decision']),
            execution='RECOMMENDATION_ONLY',accounting=traffic.queue.accounting())
        assert not any(report['real_requests'].values())
        if output:
            output=Path(output);output.mkdir(parents=True,exist_ok=False)
            (output/'here-closed.json').write_text(json.dumps(closed_fixture,indent=2)+'\n')
            (output/'here-open.json').write_text(json.dumps(dict(provenance='MOCKED_HERE',**frames),indent=2)+'\n')
            (output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
        return report
    finally:
        traffic.close();service.store.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(demonstrate(args.output),indent=2))


if __name__=='__main__':
    main()
