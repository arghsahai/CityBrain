from types import SimpleNamespace
from citybrain.demo import emit
from citybrain.dashboard.server import reduce_events


def test_optional_telemetry_failure_is_contained(tmp_path):
    runtime = SimpleNamespace(now=301)
    # Disconnected observations and unwritable output cannot propagate into control.
    assert emit(object(), runtime, tmp_path/'missing'/'events.jsonl') is False
    assert runtime.now == 301


def test_demo_replay_selects_observed_snapshot():
    state = reduce_events([
        dict(action='DEMO_CONFIG', simulation_time=0, demo_config={'label': 'DEMO'}),
        dict(action='DEMO_SNAPSHOT', simulation_time=301, demo={'vehicles': [{'id': 'ambulance0'}], 'signals': [{'state': 'ryG'}]}),
        dict(action='TERMINAL', simulation_time=425, terminal_outcome='SUCCESS')])
    assert state['demo_config']['label'] == 'DEMO'
    assert state['demo']['observed_time'] == 301
    assert state['demo']['signals'][0]['state'] == 'ryG'
    assert state['terminal']['outcome'] == 'SUCCESS'


def test_optional_snapshot_disk_failure_is_contained(tmp_path, monkeypatch):
    import citybrain.demo as demo
    monkeypatch.setattr(demo, 'observe', lambda *args: {'vehicles': [], 'signals': []})
    runtime = SimpleNamespace(now=316)
    assert demo.emit(object(), runtime, tmp_path/'missing'/'events.jsonl') is False
    assert runtime.now == 316
