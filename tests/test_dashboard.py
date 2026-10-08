"""Read-only viewer contracts; runtime is not imported by the dashboard."""
import ast
import json
from pathlib import Path
import threading
import urllib.request
import urllib.error

import pytest
from citybrain.dashboard.server import EvidenceReader, make_server, reduce_events


@pytest.fixture
def evidence():
    root=Path('data/output/integration/exception-safety-hotfix-smokes')
    if not root.exists():
        import tarfile
        with tarfile.open('docs/final-integration-evidence.tar.gz') as archive:
            return {s:[json.loads(line) for line in archive.extractfile(f'final-catalog-v1/{s}/runtime/events.jsonl').read().splitlines()] for s in ['S05','S06','S08']}
    return {s:[json.loads(line) for line in (root/s/'runtime/events.jsonl').read_text().splitlines()] for s in ['S05','S06','S08']}


@pytest.mark.parametrize('scenario,outcome,revisions',[('S05','SUCCESS',[0,1]),('S06','NO_ROUTE',[0,1]),('S08','SUCCESS',[0,1,2])])
def test_real_saved_evidence_has_correct_plans_and_terminal(evidence,scenario,outcome,revisions):
    state=reduce_events(evidence[scenario])
    assert state['terminal']['outcome']==outcome
    assert [p['plan']['revision'] for p in state['plans']]==revisions
    assert state['execution']['verification']=='VERIFIED'
    assert state['decision']['candidate_scores'] is not None


def test_partial_line_invalid_line_rotation_and_missing_file(tmp_path):
    path=tmp_path/'events.jsonl';r=EvidenceReader(path)
    assert r.snapshot()['read_error']
    event={'action':'PLAN_ACCEPTED','simulation_time':301,'accepted_plan':{'revision':0}}
    data=json.dumps(event).encode()
    path.write_bytes(data[:20]);assert r.snapshot()['record_count']==0
    with path.open('ab') as f:f.write(data[20:]+b'\nnot-json\n')
    state=r.snapshot();assert state['record_count']==1 and state['parse_errors']
    path.write_text('{"action":"TERMINAL","simulation_time":425,"terminal_outcome":"SUCCESS"}\n')
    assert r.snapshot()['terminal']['outcome']=='SUCCESS'
    path.unlink();assert r.snapshot()['read_error']


def test_replay_does_not_reveal_future(evidence,tmp_path):
    p=tmp_path/'events.jsonl';p.write_text(''.join(json.dumps(e)+'\n' for e in evidence['S08']))
    reader=EvidenceReader(p)
    assert reader.snapshot(True,301)['plan']['revision']==0
    assert reader.snapshot(True,311)['plan']['revision']==1
    assert reader.snapshot(True,316)['plan']['revision']==2
    assert reader.snapshot(True,316)['terminal'] is None
    assert reader.snapshot(True,425)['terminal']['outcome']=='SUCCESS'


def test_server_get_only_no_arbitrary_files(tmp_path):
    p=tmp_path/'absent.jsonl';server=make_server(p,0)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        with urllib.request.urlopen(base+'/api/state') as response:
            data=json.load(response);assert data['read_error'] and data['traci_status'].startswith('UNKNOWN')
        with urllib.request.urlopen(base+'/') as response: assert b'LIVE CONTROL CENTER' in response.read()
        for request in [urllib.request.Request(base+'/api/state',data=b'command=reroute'),base+'/../../citybrain/main.py']:
            with pytest.raises(urllib.error.HTTPError):urllib.request.urlopen(request)
        assert not p.exists()
    finally:server.shutdown();server.server_close();thread.join()


def test_dashboard_cannot_import_runtime_or_traci():
    for p in Path('citybrain/dashboard').glob('*.py'):
        tree=ast.parse(p.read_text())
        imports=[]
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):imports.extend(a.name for a in n.names)
            if isinstance(n,ast.ImportFrom):imports.append(n.module or '')
        assert not any(i.startswith(('traci','sumolib','citybrain.main','citybrain.core','citybrain.planner')) for i in imports)
