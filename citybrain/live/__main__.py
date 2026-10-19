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
    args,remaining=parser.parse_known_args()
    if args.mode=='simulation':
        return subprocess.call([str(ROOT/'tools/run_chennai.sh'),'--mode','simulation',*(['--port',str(args.port)] if args.port else []),*remaining])
    if remaining:
        parser.error('Unrecognized live-mode arguments')
    try:
        credentials=Credentials(os.environ.get('CITYBRAIN_OPERATOR_TOKEN'),os.environ.get('CITYBRAIN_HOSPITAL_TOKEN'),os.environ.get('CITYBRAIN_HOSPITAL_ID'))
        store=Store(args.database)
        service=LiveService(store=store)
        service.traffic=OfflineTraffic(service.graph,service.clock,args.traffic_recording)
        server=make_server(service,credentials,args.port if args.port is not None else 8784)
    except ValueError as error:
        parser.error(str(error))
    print(f'CityBrain LIVE DATA prototype: http://127.0.0.1:{server.server_port}',flush=True)
    print('Provider requests DISABLED. USER_SELECTED positions. No real dispatch. Ctrl-C to stop.',flush=True)
    if not credentials.operator:
        print('Operator actions disabled: configure CITYBRAIN_OPERATOR_TOKEN (32+ characters).',flush=True)
    try:
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
