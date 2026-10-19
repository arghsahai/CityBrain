"""Explicit dual-mode entry point; live mode never starts SUMO."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from citybrain.chennai.network import ROOT
from .server import Credentials,make_server
from .service import LiveService
from .store import Store
from .traffic import OfflineTraffic


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['simulation','live'],required=True)
    parser.add_argument('--port',type=int)
    parser.add_argument('--database',default=str(Path.home()/'.local/share/citybrain/v4/state.sqlite'))
    parser.add_argument('--traffic-recording',help='Local normalized recording; never a provider request')
    parser.add_argument('--here',action='store_true',help='Select bounded HERE ingestion; requests remain disabled without all gates')
    parser.add_argument('--here-fixture',help='Local declared HERE-format fixture; always REPLAY')
    parser.add_argument('--authorize-here-requests',action='store_true')
    parser.add_argument('--here-license-confirmed',action='store_true')
    parser.add_argument('--here-area',nargs=4,type=float,metavar=('WEST','SOUTH','EAST','NORTH'))
    parser.add_argument('--here-max-requests',type=int)
    parser.add_argument('--here-flow-limit',type=int)
    parser.add_argument('--here-incident-limit',type=int)
    parser.add_argument('--here-poll-seconds',type=float,default=60)
    parser.add_argument('--here-session-seconds',type=float,default=900)
    args,remaining=parser.parse_known_args()
    if args.mode=='simulation':
        if args.here or args.here_fixture or args.authorize_here_requests or args.here_license_confirmed or args.here_area or args.here_max_requests is not None:
            parser.error('HERE live recommendation options cannot be used in simulation mode')
        return subprocess.call([str(ROOT/'tools/run_chennai.sh'),'--mode','simulation',*(['--port',str(args.port)] if args.port else []),*remaining])
    if remaining:
        parser.error('Unrecognized live-mode arguments')
    try:
        credentials=Credentials(os.environ.get('CITYBRAIN_OPERATOR_TOKEN'),os.environ.get('CITYBRAIN_HOSPITAL_TOKEN'),os.environ.get('CITYBRAIN_HOSPITAL_ID'))
        store=Store(args.database)
        service=LiveService(store=store)
        if args.here or args.here_fixture:
            if args.traffic_recording:
                parser.error('Choose HERE ingestion or normalized offline recording')
            from .here import HERETraffic
            service.traffic=HERETraffic(service.graph,service.clock,fixture=args.here_fixture,
                on_update=lambda:service.reassess('HERE_OBSERVATIONS_UPDATED'),
                area=args.here_area,authorized=args.authorize_here_requests,licensed=args.here_license_confirmed,
                max_requests=args.here_max_requests if args.here_max_requests is not None else 20 if args.here_fixture else 0,
                flow_limit=args.here_flow_limit,incident_limit=args.here_incident_limit,
                poll_seconds=args.here_poll_seconds,session_seconds=args.here_session_seconds)
        else:
            if args.authorize_here_requests or args.here_license_confirmed:
                parser.error('Explicit --here selection is required')
            service.traffic=OfflineTraffic(service.graph,service.clock,args.traffic_recording)
        server=make_server(service,credentials,args.port if args.port is not None else 8784)
    except ValueError as error:
        parser.error(str(error))
    print(f'CityBrain LIVE DATA prototype: http://127.0.0.1:{server.server_port}',flush=True)
    print('Traffic access: '+service.traffic.snapshot().get('provider_access','DISABLED')+'. USER_SELECTED positions. No real dispatch. Ctrl-C to stop.',flush=True)
    if not credentials.operator:
        print('Operator actions disabled: configure CITYBRAIN_OPERATOR_TOKEN (32+ characters).',flush=True)
    try:
        if args.here or args.here_fixture:
            service.traffic.start()
        server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        service.traffic.close()
        store.close()
    return 0


if __name__=='__main__':
    sys.exit(main())
