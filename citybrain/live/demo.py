#!/usr/bin/env python3
"""Disposable local V4 test workflow. Never a provider or emergency API client."""
import argparse
import json
import os
from urllib.request import Request,build_opener
from urllib.parse import urlparse
from citybrain.chennai.network import PILOT
from citybrain.chennai.traffic.provider import NoRedirect
from citybrain.live.graph import PilotGraph,LiveError
from citybrain.live.traffic import OfflineTraffic


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='http://127.0.0.1:8784')
    parser.add_argument('--scenario',choices=['seed','closure','reopen','future','outage','recover'],required=True)
    parser.add_argument('--edge',help='Directed edge for the offline condition (printed by seed)')
    args=parser.parse_args()
    url=urlparse(args.base)
    if url.scheme!='http' or url.hostname not in {'127.0.0.1','localhost'} or url.username or url.password or url.path or url.query or url.fragment:
        parser.error('Only a loopback HTTP origin is allowed')
    token=os.environ.get('CITYBRAIN_OPERATOR_TOKEN','')
    if len(token)<32:
        parser.error('Configure CITYBRAIN_OPERATOR_TOKEN; do not pass tokens in command arguments')
    opener=build_opener(NoRedirect())
    def call(path,body=None):
        request=Request(args.base+'/api/live/'+path,data=json.dumps(body).encode() if body is not None else None,
            headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
        with opener.open(request,timeout=5) as response:
            return json.load(response)
    if args.scenario=='seed':
        graph=PilotGraph()
        metadata=json.loads((PILOT/'network/metadata.json').read_text())
        path=next(iter(metadata['routes'].values()))
        start,end=path[0],path[-1]
        incident=call('incidents',dict(test=True,confirmed=True,coordinates=graph.point_at(end,.5),type='ROAD_COLLISION',description='Disposable V4 scripted TEST; no real accident'))
        call('verify',dict(id=incident['id'],status='VERIFIED_FOR_TESTING'))
        call('position',dict(source='USER_SELECTED',coordinates=graph.point_at(start,.5),edge=start))
        result=call('recommend',dict(leg='AMBULANCE_TO_INCIDENT',incident_id=incident['id'],incident_edge=end))
        traffic=OfflineTraffic(graph)
        demo_edge=None
        for eid in result['route'][1:-1]:
            eligible=traffic.inject(dict(edge=eid,condition='CLOSURE'))['costs'].get(eid,{}).get('blocked')
            if not eligible:
                continue
            try:
                alternative=graph.route(dict(edge=start,fraction=.5),dict(edge=end,fraction=.5),{eid:{'blocked':True}})
                if eid not in alternative['route']:
                    demo_edge=eid;break
            except LiveError:
                continue
        traffic.close()
        print(json.dumps(dict(scenario='SYNTHETIC_TEST',recommendation_id=result['id'],status=result['status'],
            estimated_edges=result['estimated_edges'],eta_seconds=result['eta_seconds'],demo_edge=demo_edge),indent=2))
    else:
        conditions={'closure':'CLOSURE','reopen':'REOPEN','future':'FUTURE','outage':'OUTAGE','recover':'FLOW'}
        if args.scenario!='outage' and not args.edge:
            parser.error('--edge is required (use demo_edge printed by seed)')
        result=call('traffic-test',dict(edge=args.edge,condition=conditions[args.scenario]))
        state=call('state')
        recommendation=state['recommendation'] or {}
        print(json.dumps(dict(source=result['source'],active_closures=len(result['active_closures']),
            quarantined=result['quarantine_count'],provider_status=result['status'],
            recommendation_status=recommendation.get('status'),reason=recommendation.get('reason'),
            route=recommendation.get('route')),indent=2))


if __name__=='__main__':
    main()
