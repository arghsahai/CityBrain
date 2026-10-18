import ast
from pathlib import Path
from citybrain.live.signal_audit import audit


def test_signal_inventory_denies_actuation():
    result=audit()
    assert len(result['signals'])==2
    assert result['actuation_implemented'] is False
    assert all(s['status']=='ADVISORY_ONLY' and not s['eligible_for_priority'] for s in result['signals'])
    assert all(s['recovery_contract']=='NOT_VERIFIED' for s in result['signals'])


def test_live_modules_have_no_simulation_execution_imports():
    # Enforce the dependency boundary, rather than mock a simulation and assume
    # no hidden physical side effects happened.
    root=Path(__file__).resolve().parents[1]/'citybrain/live'
    forbidden=('traci','citybrain.core','citybrain.runtime','citybrain.chennai.runtime')
    for path in root.glob('*.py'):
        tree=ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                names=[a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom):
                names=[node.module or '']
            else:
                continue
            assert not any(name==prefix or name.startswith(prefix+'.') for name in names for prefix in forbidden),path
